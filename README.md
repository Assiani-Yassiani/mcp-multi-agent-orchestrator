# Multi-Agent MCP – Gmail, Calendar, Web & GitHub Orchestrator

Système multi-agent basé sur **Google ADK (Agent Development Kit)** et **A2A (Agent-to-Agent)**, exposé via une **API Flask** avec une interface web moderne.  
L’orchestrateur IA coordonne plusieurs agents spécialisés (Gmail, Calendar, Web Search, GitHub, Conversation) pour exécuter des tâches complexes de manière unifiée.

Les agents sont **MCP-compliant**, ce qui permet de les connecter facilement à d’autres outils et serveurs MCP.

---

## 🎥 Démonstration

### 🖼 Aperçu de l’interface

[![Multi-Agent UI](mcp.png)](https://vimeo.com/1142186208)
> Cliquez sur l’image pour ouvrir la vidéo de démonstration sur Vimeo.

Tableau de bord temps réel montrant :
- l’état des agents (Email, Calendar, Web Search, GitHub, Conversational),
- un chat centralisé piloté par l’orchestrateur IA,
- l’historique des actions exécutées par les agents.

### 🎬 Vidéo de démonstration

[▶ Voir la démo vidéo sur Vimeo](https://vimeo.com/1142186208)

---

## 🤖 Description du projet

Ce projet implémente un **système multi-agent MCP** capable de :

- Gérer vos **emails Gmail** (lecture, recherche, envoi)
- Interagir avec **Google Calendar** (liste, création, suppression d’événements, disponibilité)
- Effectuer des **recherches web** via DuckDuckGo
- Consommer l’API **GitHub** (repos, issues, trending, stats, etc.)
- Fournir une **interface de chat moderne** pour piloter tous les agents à travers un **Orchestrateur IA**

Les agents exposent une API A2A et peuvent être réutilisés ou branchés sur d’autres orchestrateurs ou systèmes MCP.

---

## 🧩 Architecture Multi-Agent

### 🧠 Orchestrator Agent

- Rôle : **cerveau central du système**
- Analyse la requête utilisateur et la route vers :
  - Email Agent
  - Calendar Agent
  - Web Search Agent
  - GitHub Agent
  - Conversational Agent
- Agrège et reformate les réponses des agents
- Garantit un format de réponse standardisé pour le frontend (UI + API)

---

### 📧 Email Agent (Gmail)

- Liste les derniers emails
- Recherche d’emails par mots-clés
- Envoi d’emails Gmail
- Utilise l’API Gmail avec :
  - un fichier `credentials.json`
  - un token combiné `token_combined.pickle` pour l’authentification

---

### 📅 Calendar Agent (Google Calendar)

- Liste des événements à venir
- Création d’événements
- Suppression d’événements
- Vérification de la disponibilité sur une plage de dates
- Intégration avec l’API Google Calendar (OAuth 2.0)

---

### 🔍 Web Search Agent

- Recherche web via **DuckDuckGo Search**
- Retourne les résultats formatés :
  - titre
  - URL
  - court extrait (snippet)
- Utilisé par l’orchestrateur pour enrichir le contexte des réponses

---

### 🐙 GitHub Agent

- Recherche de dépôts GitHub
- Informations sur un utilisateur
- Statistiques d’un repo :
  - stars, forks, issues, langage principal, taille, etc.
- Liste des repos d’un utilisateur
- Création et recherche d’issues
- Simulation de “trending” repos par langage et période (daily / weekly / monthly) via recherche filtrée

---

### 💬 Conversational Agent

- Agent “généraliste” basé sur LLM pour les réponses naturelles
- Explique, reformule, propose des actions et guide l’utilisateur
- Peut déclencher d’autres agents (Email, Calendar, GitHub, Web Search) selon la requête
- Respecte les formats de réponse utilisés par les autres agents pour garder une interface cohérente

---

## 🛠️ Technologies principales

- **Python 3**  
- **Flask** – API backend & orchestrateur  
- **Google ADK** – définition et exécution des agents  
- **A2A (Agent-to-Agent)** – communication entre agents  
- **MCP** – compatibilité avec l’écosystème Model Context Protocol  
- **Gmail API & Google Calendar API**  
- **DuckDuckGo Search**  
- **GitHub REST API**  
- Frontend web moderne (HTML/CSS/JS) pour le tableau de bord et le chat

---

> 💡 Ce repo est une base complète pour expérimenter avec des systèmes **agentic AI** multi-sources (email, calendrier, web, GitHub) orchestrés par une seule interface IA.
