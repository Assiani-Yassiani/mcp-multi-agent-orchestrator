# Multi-Agent MCP – Gmail, Calendar, Web & GitHub Orchestrator

Système multi-agent basé sur **Google ADK (Agent Development Kit)** et **A2A (Agent-to-Agent)**, exposé via une **API Flask** avec une interface web moderne.  
L’orchestrateur IA coordonne plusieurs agents spécialisés (Gmail, Calendar, Web Search, GitHub, Conversation) pour exécuter des tâches complexes de manière unifiée.

---

## 🎥 Démonstration

### 🖼 Aperçu de l’interface

![Multi-Agent UI](mcp.png)

> Tableau de bord temps réel montrant l’état des agents (Email, Calendar, Web Search, GitHub, Conversational) et un chat centralisé piloté par l’orchestrateur.

### 🎬 Vidéo de démonstration

<video controls width="100%" src="demo/multiagent_demo.mp4](https://vimeo.com/manage/videos/1142186208)">
  Votre navigateur ne supporte pas la lecture vidéo intégrée.
</video>

> Vidéo montrant l’orchestrateur qi :
> - Liste les emails Gmail
> - Affiche les événements Google Calendar
> - Lance des recherches web
> - Analyse des repositories GitHub
> - Répond via l’interface de chat

*(Remplace `assets/multiagent_ui.png` et `demo/multiagent_demo.mp4` par les noms réels de tes fichiers.)*

---

## 🤖 Description du projet

Ce projet implémente un **système multi-agent MCP** capable de :

- Gérer vos **emails Gmail** (lecture, recherche, envoi)
- Interagir avec **Google Calendar** (liste, création, suppression d’événements, disponibilité)
- Effectuer des **recherches web** via DuckDuckGo
- Consommer l’API **GitHub** (repos, issues, trending, stats, etc.)
- Fournir une **interface de chat moderne** pour piloter tous les agents à travers un **Orchestrateur IA**

Les agents exposent une API A2A et sont **MCP-compliant** : ils peuvent être branchés sur d’autres systèmes MCP si besoin.

---

## 🧩 Architecture Multi-Agent

### 🧠 Orchestrator Agent

- Rôle : **cerveau central**
- Analyse la requête utilisateur et route vers :
  - Email Agent
  - Calendar Agent
  - Web Search Agent
  - GitHub Agent
  - Conversational Agent
- Vérifie et reformate les réponses des autres agents (formats standardisés pour le frontend)

### 📧 Email Agent (Gmail)

- Liste les derniers emails
- Recherche d’emails par mots-clés
- Envoi d’emails Gmail directement
- Utilise l’API Gmail avec un `credentials.json` et un token combiné (`token_combined.pickle`)

### 📅 Calendar Agent (Google Calendar)

- Liste des événements à venir
- Création d’événements
- Suppression d’événements
- Vérification de la disponibilité sur une date donnée

### 🔍 Web Search Agent

- Recherche web via **DuckDuckGo Search**
- Retourne les résultats formatés (titre, URL, snippet)

### 🐙 GitHub Agent

- Recherche de repos GitHub
- Infos utilisateur
- Statistiques d’un repo (stars, forks, issues, langue, taille…)
- Liste des repos d’un utilisateur
- Création d’issues
- Recherche d’issues
- “Trending” repos par langage et période (daily/weekly/monthly – simulation via critères de recherche)

### 💬 Conversational Agent

- Agent “généraliste” pour les réponses naturelles
- Explique, reformule, propose des actions, guide l’utilisateur
- Respecte les formats des autres agents lorsqu’il parle d’emails, calendrier, GitHub, etc.

---

## 🖥️ Interface Web (Flask)

Le projet expose une **API Flask** + une **single-page UI** minimaliste :

- **Vue agents** : liste des agents, ports, statut “online”
- **Chat central** : messages utilisateur / réponses orchestrateur
- **Actions rapides** :
  - “Mes emails récents”
  - “Calendrier aujourd’hui”
  - “Repos Python GitHub”
  - “News IA”
  - “Tutoriels ML”
- **Stats live** :
  - Nombre de requêtes
  - Uptime

Endpoints principaux :

- `GET /` → Interface web (chat + dashboard agents)
- `POST /api/chat` → Envoie un message à l’orchestrateur
- `GET /api/health` → Health check (status des agents)

---

## 🛠️ Stack Technique

- **Langage :** Python 3
- **Frameworks backend :**
  - Flask + Flask-CORS
  - Uvicorn + Starlette (serveurs A2A)
- **IA / Orchestration :**
  - Google **Gemini 2.5 Flash**
  - Google **ADK** (`google.adk`)
  - A2A (`a2a.server`, `a2a.client`)
- **APIs externes :**
  - **Gmail API**
  - **Google Calendar API**
  - **GitHub API** (`PyGithub`)
  - **DuckDuckGo Search** (`duckduckgo_search`)
- **Auth & OAuth :**
  - `google-auth`, `google-auth-oauthlib`, `google-api-python-client`
- **Autres :**
  - `nest_asyncio`, `httpx`, `pickle`, `dotenv`

---

## 🔐 Authentification & Credentials

### 1️⃣ Google (Gmail + Calendar)

Le projet utilise un **fichier `credentials.json`** (OAuth2 Desktop App) et génère un token combiné :

- `credentials.json` : à placer à la racine du projet
- `token_combined.pickle` : généré au premier lancement après consentement Google

Scopes utilisés :

- Gmail :  
  - `https://www.googleapis.com/auth/gmail.readonly`  
  - `https://www.googleapis.com/auth/gmail.send`  
  - `https://www.googleapis.com/auth/gmail.modify`
- Calendar :  
  - `https://www.googleapis.com/auth/calendar.readonly`  
  - `https://www.googleapis.com/auth/calendar.events`

### 2️⃣ Gemini API

La clé est lue via la variable d’environnement :

```bash
export GOOGLE_API_KEY="TA_CLE_GEMINI"
