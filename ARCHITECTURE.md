

# ARCHITECTURE.md



## 3.1 Business Architecture

**Personas :**

1. **Développeur : Alexandre** : Contexte = code quotidien avec Cursor/Claude. Frustrations = Jira trop complexe, perte de temps à changer entre plusieurs outils. Besoins = créer story en 1 tool call.
<br/>
2. **Manager : Julien** : Contexte = suit équipe 10 devs. Frustrations = rapports manuels. Besoins = filtrer stories par status/assigné.
<br/>

3. **Product Owner : Juliette** : Contexte = définit priorités. Frustrations = pas de docs templates. Besoins = créer docs "Product Vision". 
<br/>

3. **Testeur QA : Laura** : Contexte = teste stories in_review, valide bugs. Frustrations = manque visibilité stories prêtes. Besoins = filtrer stories par status/priority, ajouter commentaires
<br/>


**JTBD principal :**
En tant que Développeur, je veux créer une story via MCP depuis mon IDE afin de garder le contexte sans switcher apps.

**3 Cas d'usage concrets :**

1. **Dev** : Dans Cursor, Claude appelle `create_story()` → story créée, ID retourné pour référence code.
2. **Manager** : `GET /stories?status=in_progress&assigned_to=dev1` → liste paginée avec points.
3. **PO** : `POST /documents` avec template "Product Vision" → doc structuré créé.

**Règles métier (5) :**

1. Story points : UNIQUEMENT `[0,1,2,3,5,8,13]` (Fibonacci).
2. Impossible clôturer sprint avec stories `in_progress/in_review`.
3. Max 20 stories par sprint.
4. Story ne saute PAS d'étape workflow (`backlog→todo→in_progress→in_review→done`).
5. Une story = 1 seul sprint ACTIF (historique OK).

## 3.2 Application Architecture

**Diagramme architecture :**

```
+-------------+     MCP/REST     +-------------+     SQL      +-------------+
| Clients     | ---------------- | FastAPI     | ------------ | PostgreSQL |
| (IDE/Claude)|    (HTTP/SSE)   | (1 Service) |   (psycopg)  |             |
+-------------+                 +-------------+              +-------------+
```

**Justification : 1 service unique (REST + MCP)**. Pourquoi ? Même logique métier/services, scaling simple, moins de coûts/latence vs 2 services. Séparation concerns via modules (routes_rest.py, mcp_tools.py).

### **Endpoints REST :**


**Projet** (créer, lister)
|Méthode|Path|Params|Réponse|Erreurs|
|-|-|-|-|-|
|POST|`/projects`|`name:str(3-100)`|`{"id":uuid,"name":str}`|422 nom invalid, 409 doublon|
|GET|`/projects`|`-`|`[{"id":uuid,"name":str},...]`|-|

**Epic** (créer, lire, modifier, lister, recherche, filtre statut)
|Méthode|Path|Params|Réponse|Erreurs|
|-|-|-|-|-|
|POST|`/projects/{proj_id}/epics`|`title:str(3-200),desc:str`|`{"id":uuid,"title":str,status:"backlog"}`|404 proj, 422 title|
|GET|`/epics/{epic_id}`|`-`|`{"id":uuid,...}`|404|
|PUT|`/epics/{epic_id}`|`title:str,status:str`|`{"id":uuid,...}`|422 status|
|GET|`/projects/{proj_id}/epics`|`status:str,search:str`|`[{"id":uuid,...}]`|404|

**Story** (créer, lire, modifier, lister, recherche, filtre status/priority/assigned/sprint/points/workflow)
|Méthode|Path|Params|Réponse|Erreurs|
|-|-|-|-|-|
|POST|`/epics/{epic_id}/stories`|`title:str,desc:str,points:int[0,1,2,3,5,8,13],priority:str`|`{"id":uuid,status:"backlog"}`|422 points/status|
|GET|`/stories/{story_id}`|`-`|`{"id":uuid,title,points,...}`|404|
|PUT|`/stories/{story_id}`|`status:str,points:int,priority:str,assigned:str`|`{"id":uuid,...}`|400 workflow skip|
|GET|`/projects/{proj_id}/stories`|`status:str,priority:str,assigned:str,sprint_id:str,search:str`|`{"stories":[...],"total":int}`|404|

**Sprint** (créer, démarrer, clôturer, affecter/retirer stories)
|Méthode|Path|Params|Réponse|Erreurs|
|-|-|-|-|-|
|POST|`/projects/{proj_id}/sprints`|`name:str`|`{"id":uuid,status":"planning"}`|422|
|PUT|`/sprints/{sprint_id}/start`|`-`|`{"status":"active"}`|400 déjà active|
|PUT|`/sprints/{sprint_id}/close`|`-`|`{"status":"closed"}`|400 stories ouvertes|
|PUT|`/sprints/{sprint_id}/stories/{story_id}`|`-` (affecter)|`{"story_id":"s1","sprint_id":"sp1"}`|400 story déjà sprint|
|DELETE|`/sprints/{sprint_id}/stories/{story_id}`|`-` (retirer)|`{"message":"removed"}`|404|

**Commentaire** (ajouter story/epic, lister)
|Méthode|Path|Params|Réponse|Erreurs|
|-|-|-|-|-|
|POST|`/stories/{story_id}/comments`|`text:str(5-1000)`|`{"id":uuid,"text":str}`|422|
|POST|`/epics/{epic_id}/comments`|`text:str`|`{"id":uuid,...}`|422|
|GET|`/stories/{story_id}/comments`|`-`|`[{"id":uuid,"text":str},...]`|404|
|GET|`/epics/{epic_id}/comments`|`-`|`[...]`|404|

**Document** (créer template/vide, lire, modifier, lister, rechercher)
|Méthode|Path|Params|Réponse|Erreurs|
|-|-|-|-|-|
|POST|`/projects/{proj_id}/documents`|`type:str(problem/vision/tdr/retrospective),content:str`|`{"id":uuid,type:str,content:str}`|400 type|
|GET|`/documents/{doc_id}`|`-`|`{"id":uuid,content:str}`|404|
|PUT|`/documents/{doc_id}`|`content:str`|`{"id":uuid,...}`|-|
|GET|`/projects/{proj_id}/documents`|`type:str,search:str(ILIKE)`|`[{"id":uuid,...}]`|404|


### **Liste des tools MCP**

| Entité | Méthode | Path | Params | Réponse | Code Erreur |
|--------|---------|------|--------|---------|-------------|
| **Projet** | POST | `/projects` | `name:str` | `{"id":uuid,"name":str}` | 422 nom<3, 409 doublon |
| **Epic** | GET | `/projects/{proj_id}/epics` | `search:str` | `[{"id":uuid,"title":str,...}]` | 404 proj |
| **Story** | POST | `/epics/{epic_id}/stories` | `title:str,desc:str,points:int,priority:str` | `{"id":uuid,...}` | 422 points invalid |
| **Story** | GET | `/projects/{proj_id}/stories` | `status:str,priority:str,assigned:str,sprint_id:str,search:str` | `{"stories":[...],"total":int}` | - |
| **Sprint** | PUT | `/sprints/{id}/stories/{story_id}` | `-` | `{"status":"assigned"}` | 400 story déjà sprint |
| **Commentaire** | POST | `/stories/{story_id}/comments` | `text:str` | `{"id":uuid,"text":str}` | 422 text<10 |
| **Document** | POST | `/projects/{proj_id}/documents` | `type:str(template),content:str` | `{"id":uuid,...}` | 400 type invalid [file:1] |

**Contrat validation (toutes entités) :**

- `title: str(3-200)`, `desc: str(10-5000)`, `points: int([0,1,2,3,5,8,13])`, `priority: Literal["low","medium","high","critical"]`, `status: Literal["backlog","todo","in_progress","in_review","done"]`.
HTTP 422 + detail JSON si invalid.


## 3.3 Data Architecture

**Schéma tables PostgreSQL :**

![alt text](<Capture d’écran 2026-02-12 à 11.53.27.png>)

```sql
CREATE TABLE projects (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(100) NOT NULL UNIQUE CHECK (LENGTH(name) >= 3)
);

CREATE TABLE epics (
    id UUID PK DEFAULT gen_random_uuid(),
    project_id UUID NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    title VARCHAR(200) NOT NULL,
    status VARCHAR(20) CHECK (status IN ('backlog','done'))
);

CREATE TABLE stories (
    id UUID PK DEFAULT gen_random_uuid(),
    epic_id UUID NOT NULL REFERENCES epics(id),
    title VARCHAR(200) NOT NULL CHECK (LENGTH(title) >= 3),
    description TEXT CHECK (LENGTH(description) >= 10),
    story_points INT CHECK (story_points IN (0,1,2,3,5,8,13)),
    priority VARCHAR(20) CHECK (priority IN ('low','medium','high','critical')),
    status VARCHAR(20) CHECK (status IN ('backlog','todo','in_progress','in_review','done')),
    assigned_to VARCHAR(100)
);

CREATE TABLE sprints (
    id UUID PK DEFAULT gen_random_uuid(),
    project_id UUID NOT NULL REFERENCES projects(id),
    name VARCHAR(100) NOT NULL,
    status VARCHAR(20) CHECK (status IN ('planning','active','closed'))
);

CREATE TABLE story_sprint_history (  -- M:N historique
    story_id UUID NOT NULL REFERENCES stories(id),
    sprint_id UUID NOT NULL REFERENCES sprints(id),
    assigned_at TIMESTAMP DEFAULT NOW(),
    PRIMARY KEY (story_id, sprint_id),
    CHECK (  -- 1 sprint actif: app-level + trigger possible
        (SELECT COUNT(*) FROM story_sprint_history s2 
         WHERE s2.story_id = story_sprint_history.story_id 
         AND s2.sprint_id IN (SELECT id FROM sprints WHERE status='active')) <= 1
    )
);

CREATE TABLE comments (
    id UUID PK DEFAULT gen_random_uuid(),
    story_id UUID REFERENCES stories(id),
    epic_id UUID REFERENCES epics(id),
    text TEXT NOT NULL CHECK (LENGTH(text) >= 5),
    author VARCHAR(100)
);

CREATE TABLE documents (
    id UUID PK DEFAULT gen_random_uuid(),
    project_id UUID REFERENCES projects(id),
    type VARCHAR(50) CHECK (type IN ('problem','vision','tdr','retrospective')),
    content TEXT NOT NULL
);
```

**Relations :** projects(1:N)epics(1:N)stories(N:M)sprints(1:N), stories/epics(1:N)comments, projects(1:N)documents. **Historique stories-sprints : table jonction `story_sprint_history` + CHECK 1 actif.**

**Diagramme ERD :**

```
projects --1:N--> epics --1:N--> stories --N:M--> sprints (history)
                    |                |
                1:N comments     1:N comments
projects --1:N--> documents
```

**Index optimisés :**

```sql
CREATE INDEX idx_stories_status ON stories(status);
CREATE INDEX idx_stories_priority_assigned ON stories(priority, assigned_to);
CREATE INDEX idx_stories_sprint ON story_sprint_history(sprint_id);
CREATE INDEX idx_stories_search ON stories USING GIN(to_tsvector('simple', title || ' ' || description));
```



**Templates documents :** Seed data à migration :

```sql
INSERT INTO documents (project_id, type, content) VALUES 
('template_problem', 'problem', '# Problem Statement\n...'),
('template_vision', 'vision', '# Product Vision\n...');
```

Création copie template + edit.

## 3.4 Technology Architecture

**Diagramme déploiement GCP :**

```
GitHub Repo
     ↓ (push)
Cloud Build (eu-west1)
     ↓
Cloud Run Service (eu-west1, 1 port:8000)
     ↓ (Unix Socket + Auth Proxy)
Cloud SQL PostgreSQL (eu-west1, private IP)
```

**Tableau services GCP :**


| Service | Justification |
| :-- | :-- |
| Cloud Run | Serverless Python, auto-scale 1-10 instances, cold start <2s OK pour TP.  |
| Cloud SQL PG | Relationnel + contraintes SQL critiques pour règles métier. |
| Cloud Build | CI/CD gratuit, trigger Git, steps : uv/test/deploy.  |

**Scaling :** Cloud Run min=1 max=10 instances, CPU 1Gi memory, concurrency=80. Stratégie : request-based auto-scale.

**Connexion BDD :** **Cloud SQL Auth Proxy + Unix Socket** (`/cloudsql/...`). Justif : sécurisé (IAM, pas creds), performant.

**Pipeline CI/CD Cloud Build (cloudbuild.yaml) :**

```yaml
steps:
- name: 'gcr.io/cloud-builders/gcloud'
  args: ['uv', 'sync']
- name: 'alembic upgrade head'  # migrations
- name: 'pytest'               # tests
- name: 'gcloud run deploy'    # prod
```

**Trigger :** push main.

## 3.5 Security Architecture

**Auth REST :** **API Key** (header `X-API-Key`, stocké Secret Manager). **Justif :** Simple pour TP (vs JWT=overkill), vérifié middleware FastAPI.

**Sécurité MCP :** **Transport SSE** (`/mcp`), tools exposés publiquement mais **consentement user requis** par client Claude. Contrôle accès : même API key via header MCP.

**Matrice permissions (rôles : user/manager, cohérent REST/MCP) :**


| Rôle | Projet | Epic | Story (CRUD/Filter) | Sprint | Commentaire | Document |
| :-- | :-- | :-- | :-- | :-- | :-- | :-- |
| User | C/R/U/D (siens) | C/R/U/D | C/R/U/D (siens) | C/R/U/D | C/R (siens) | C/R/U/D |
| Manager | All | All | All | All | All | All  |

**Mesures protection :**

- **SQL injection** : SQLAlchemy params bindés + contraintes CHECK.
- **Abus** : Rate limiting FastAPI (slowapi, 100/min/IP).
- **Accès non auth** : Middleware reject 401 sans key.

**Défense en profondeur (partagée REST/MCP) :**

1. **Pydantic** : types/lengths/enums (Layer input).
2. **Logique métier** : règles workflow/points (Layer service).
3. **SQL** : CHECK/FK/UNIQUE (Layer DB).
Ex : create_story → Pydantic(points enum) → service(check workflow) → SQL(CHECK).

***