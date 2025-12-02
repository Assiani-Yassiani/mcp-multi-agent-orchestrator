

import subprocess
import time
import os

print("=" * 80)
print(" NETTOYAGE EN COURS...")
print("=" * 80 + "\n")


ports = [10024, 10025, 10026, 10027, 10028]
for port in ports:
    try:
        subprocess.run(
            f"lsof -ti:{port} | xargs kill -9", shell=True, capture_output=True
        )
        print(f"Port {port} libéré")
    except:
        pass

time.sleep(3)
print("Nettoyage terminé !\n")
import warnings

warnings.filterwarnings("ignore")


import os
import asyncio
import threading
import time
import json
import pickle
from typing import Any
import uuid
import httpx
import nest_asyncio
import uvicorn
from datetime import datetime, timedelta, timezone
from flask import Flask, request, jsonify
from flask_cors import CORS  

# ============================================================
#  CONFIGURATION CRITIQUE - AVANT TOUS LES IMPORTS ADK
# ============================================================

os.environ["GOOGLE_API_KEY"] = ""

# Maintenant importer Google ADK
from google.adk.agents import Agent
from google.adk.agents.remote_a2a_agent import RemoteA2aAgent
from google.adk.artifacts import InMemoryArtifactService
from google.adk.memory.in_memory_memory_service import InMemoryMemoryService
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService

# A2A imports
from a2a.server.apps import A2AStarletteApplication
from a2a.server.request_handlers import DefaultRequestHandler
from a2a.server.tasks import InMemoryTaskStore
from a2a.types import (
    AgentCapabilities,
    AgentCard,
    AgentSkill,
    MessageSendParams,
    SendMessageRequest,
)
from a2a.utils.constants import AGENT_CARD_WELL_KNOWN_PATH
from a2a.client import A2AClient

from google.adk.a2a.executor.a2a_agent_executor import (
    A2aAgentExecutor,
    A2aAgentExecutorConfig,
)

# Google Auth imports
from google.auth.transport.requests import Request
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

# Imports externes
from duckduckgo_search import DDGS
from github import Github
from dotenv import load_dotenv

nest_asyncio.apply()
load_dotenv()

print(" Imports terminés !")

# ============================================================
# CONFIGURATION
# ============================================================

MODEL_NAME = "gemini-2.5-flash"
EMAIL_AGENT_PORT = 10024
CALENDAR_AGENT_PORT = 10025
WEB_SEARCH_AGENT_PORT = 10026
GITHUB_AGENT_PORT = 10027
ORCHESTRATOR_AGENT_PORT = 10028


GITHUB_TOKEN = os.getenv(
    "GITHUB_TOKEN",
    "",
)

print(" Configuration chargée !")
print(f" Modèle: {MODEL_NAME}")
print(f"API Key configurée via GOOGLE_API_KEY")
print(
    f"🔧 Ports: {EMAIL_AGENT_PORT}, {CALENDAR_AGENT_PORT}, {WEB_SEARCH_AGENT_PORT}, {GITHUB_AGENT_PORT}, {ORCHESTRATOR_AGENT_PORT}"
)

# ============================================================
# AUTHENTIFICATION GMAIL + CALENDAR
# ============================================================

GMAIL_SCOPES = [
    "https://www.googleapis.com/auth/gmail.readonly",
    "https://www.googleapis.com/auth/gmail.send",
    "https://www.googleapis.com/auth/gmail.modify",
]

CALENDAR_SCOPES = [
    "https://www.googleapis.com/auth/calendar.readonly",
    "https://www.googleapis.com/auth/calendar.events",
]

ALL_SCOPES = GMAIL_SCOPES + CALENDAR_SCOPES


def get_google_credentials(token_file="token_combined.pickle"):
    """Obtenir les credentials pour Gmail + Calendar"""
    creds = None

    if os.path.exists(token_file):
        with open(token_file, "rb") as token:
            creds = pickle.load(token)

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            if not os.path.exists("credentials.json"):
                print("  credentials.json introuvable - Gmail/Calendar désactivés")
                return None

            flow = InstalledAppFlow.from_client_secrets_file(
                "credentials.json",
                ALL_SCOPES,
            )
            creds = flow.run_local_server(port=0)

        with open(token_file, "wb") as token:
            pickle.dump(creds, token)

    return creds


GOOGLE_CREDS = get_google_credentials()

if GOOGLE_CREDS:
    print("Gmail & Calendar authentifiés !")
else:
    print(" Gmail & Calendar non disponibles")

# ============================================================
# FONCTIONS GMAIL
# ============================================================


def gmail_list_emails(max_results: int = 5) -> str:
    """Liste les emails récents"""
    if not GOOGLE_CREDS:
        return " Gmail non configuré. Ajoutez credentials.json"

    try:
        service = build("gmail", "v1", credentials=GOOGLE_CREDS)
        results = (
            service.users()
            .messages()
            .list(userId="me", maxResults=max_results)
            .execute()
        )

        messages = results.get("messages", [])
        if not messages:
            return "📭 Aucun email trouvé"

        output = f"📧 {len(messages)} emails récents:\n\n"

        for i, msg in enumerate(messages, 1):
            message = (
                service.users()
                .messages()
                .get(
                    userId="me",
                    id=msg["id"],
                    format="metadata",
                    metadataHeaders=["From", "Subject", "Date"],
                )
                .execute()
            )

            headers = message["payload"]["headers"]
            subject = next(
                (h["value"] for h in headers if h["name"] == "Subject"), "Sans sujet"
            )
            sender = next(
                (h["value"] for h in headers if h["name"] == "From"), "Inconnu"
            )
            snippet = message.get("snippet", "")[:100]

            output += f"{i}. {subject}\n"
            output += f"   De: {sender}\n"
            output += f"   Aperçu: {snippet}...\n\n"

        return output

    except Exception as e:
        return f"❌ Erreur Gmail: {str(e)}"


def gmail_search_emails(query: str, max_results: int = 5) -> str:
    """Recherche des emails"""
    if not GOOGLE_CREDS:
        return "❌ Gmail non configuré"

    try:
        service = build("gmail", "v1", credentials=GOOGLE_CREDS)
        results = (
            service.users()
            .messages()
            .list(userId="me", q=query, maxResults=max_results)
            .execute()
        )

        messages = results.get("messages", [])
        if not messages:
            return f"📭 Aucun email trouvé pour: {query}"

        output = f"🔍 Résultats pour '{query}': {len(messages)} email(s)\n\n"

        for i, msg in enumerate(messages, 1):
            message = (
                service.users()
                .messages()
                .get(
                    userId="me",
                    id=msg["id"],
                    format="metadata",
                    metadataHeaders=["From", "Subject", "Date"],
                )
                .execute()
            )

            headers = message["payload"]["headers"]
            subject = next(
                (h["value"] for h in headers if h["name"] == "Subject"), "Sans sujet"
            )
            sender = next(
                (h["value"] for h in headers if h["name"] == "From"), "Inconnu"
            )

            output += f"{i}. {subject}\n   De: {sender}\n\n"

        return output

    except Exception as e:
        return f"❌ Erreur: {str(e)}"


def gmail_send_email(to: str, subject: str, body: str) -> str:
    """Envoyer un email directement sans confirmation
    Args:
        to: Adresse email du destinataire
        subject: Sujet de l'email
        body: Contenu de l'email
    """
    if not GOOGLE_CREDS:
        return "❌ Gmail non configuré"

    try:
        from email.mime.text import MIMEText
        import base64

        service = build("gmail", "v1", credentials=GOOGLE_CREDS)

        # Créer le message
        message = MIMEText(body)
        message["to"] = to
        message["subject"] = subject

        # Encoder en base64
        raw_message = base64.urlsafe_b64encode(message.as_bytes()).decode()

        # Envoyer
        send_message = (
            service.users()
            .messages()
            .send(userId="me", body={"raw": raw_message})
            .execute()
        )

        return f"✅ Email envoyé !\n📧 À: {to}\n📝 Sujet: {subject}"

    except Exception as e:
        return f"❌ Erreur d'envoi: {str(e)}"


# ============================================================
# FONCTIONS CALENDAR
# ============================================================


def calendar_list_events(max_results: int = 5) -> str:
    """Liste les événements à venir"""
    if not GOOGLE_CREDS:
        return "❌ Calendar non configuré"

    try:
        service = build("calendar", "v3", credentials=GOOGLE_CREDS)
        now = datetime.now(timezone.utc).isoformat()

        events_result = (
            service.events()
            .list(
                calendarId="primary",
                timeMin=now,
                maxResults=max_results,
                singleEvents=True,
                orderBy="startTime",
            )
            .execute()
        )

        events = events_result.get("items", [])
        if not events:
            return "📭 Aucun événement à venir"

        output = f"📅 {len(events)} événements à venir:\n\n"

        for i, event in enumerate(events, 1):
            start = event["start"].get("dateTime", event["start"].get("date"))
            summary = event.get("summary", "Sans titre")

            try:
                start_dt = datetime.fromisoformat(start.replace("Z", "+00:00"))
                formatted_date = start_dt.strftime("%d/%m/%Y à %H:%M")
            except:
                formatted_date = start

            output += f"{i}. {summary}\n   📅 {formatted_date}\n\n"

        return output

    except Exception as e:
        return f"❌ Erreur: {str(e)}"


def calendar_create_event(
    summary: str, start_time: str, end_time: str, description: str = ""
) -> str:
    """Créer un nouvel événement
    Args:
        summary: Titre de l'événement
        start_time: Format ISO 8601 (ex: 2024-12-15T10:00:00)
        end_time: Format ISO 8601
        description: Description optionnelle
    """
    if not GOOGLE_CREDS:
        return "❌ Calendar non configuré"

    try:
        service = build("calendar", "v3", credentials=GOOGLE_CREDS)

        event = {
            "summary": summary,
            "description": description,
            "start": {"dateTime": start_time, "timeZone": "UTC"},
            "end": {"dateTime": end_time, "timeZone": "UTC"},
        }

        created_event = (
            service.events().insert(calendarId="primary", body=event).execute()
        )
        return f"✅ Événement créé: {summary}\n📅 {start_time}\n🔗 {created_event.get('htmlLink')}"

    except Exception as e:
        return f"❌ Erreur: {str(e)}"


def calendar_delete_event(event_id: str) -> str:
    """Supprimer un événement"""
    if not GOOGLE_CREDS:
        return "❌ Calendar non configuré"

    try:
        service = build("calendar", "v3", credentials=GOOGLE_CREDS)
        service.events().delete(calendarId="primary", eventId=event_id).execute()
        return f"✅ Événement supprimé"
    except Exception as e:
        return f"❌ Erreur: {str(e)}"


def calendar_check_availability(date: str) -> str:
    """Vérifier la disponibilité pour une date
    Args:
        date: Format YYYY-MM-DD
    """
    if not GOOGLE_CREDS:
        return "❌ Calendar non configuré"

    try:
        service = build("calendar", "v3", credentials=GOOGLE_CREDS)

        time_min = f"{date}T00:00:00Z"
        time_max = f"{date}T23:59:59Z"

        events_result = (
            service.events()
            .list(
                calendarId="primary",
                timeMin=time_min,
                timeMax=time_max,
                singleEvents=True,
                orderBy="startTime",
            )
            .execute()
        )

        events = events_result.get("items", [])

        if not events:
            return f"✅ {date}: Totalement disponible toute la journée"

        output = f"📅 Disponibilité pour {date}:\n\n"
        output += f"🔴 {len(events)} événement(s) planifié(s):\n"

        for event in events:
            start = event["start"].get("dateTime", event["start"].get("date"))
            end = event["end"].get("dateTime", event["end"].get("date"))
            summary = event.get("summary", "Sans titre")
            output += f"   • {summary}: {start} → {end}\n"

        return output

    except Exception as e:
        return f"❌ Erreur: {str(e)}"


# ============================================================
# FONCTIONS WEB SEARCH
# ============================================================


def web_search_tool(query: str, max_results: int = 5) -> str:
    """Recherche web avec DuckDuckGo"""
    try:
        ddgs = DDGS()
        results = list(ddgs.text(query, max_results=max_results))

        output = f"🔍 Résultats pour: {query}\n\n"
        for i, r in enumerate(results, 1):
            output += f"{i}. {r.get('title', '')}\n"
            output += f"   🔗 {r.get('href', '')}\n"
            output += f"   {r.get('body', '')[:150]}...\n\n"

        return output
    except Exception as e:
        return f"❌ Erreur de recherche: {str(e)}"


# ============================================================
# FONCTIONS GITHUB
# ============================================================


def github_search_repos(query: str, max_results: int = 5) -> str:
    """Recherche de repositories GitHub"""
    try:
        g = Github(GITHUB_TOKEN) if GITHUB_TOKEN else Github()
        repos = g.search_repositories(query=query)

        output = f"🐙 Repositories pour: {query}\n\n"
        for i, repo in enumerate(list(repos[:max_results]), 1):
            output += f"{i}. {repo.full_name}\n"
            output += f"   ⭐ {repo.stargazers_count:,} stars\n"
            output += f"   📝 {repo.description or 'Pas de description'}\n"
            output += f"   🔗 {repo.html_url}\n\n"

        return output
    except Exception as e:
        return f"❌ Erreur GitHub: {str(e)}"


def github_get_user_info(username: str) -> str:
    """Infos utilisateur GitHub"""
    try:
        g = Github(GITHUB_TOKEN) if GITHUB_TOKEN else Github()
        user = g.get_user(username)

        output = f"🐙 Utilisateur: {username}\n\n"
        output += f"👤 Nom: {user.name or 'N/A'}\n"
        output += f"📝 Bio: {user.bio or 'N/A'}\n"
        output += f"📊 Repos: {user.public_repos}\n"
        output += f"👥 Followers: {user.followers:,}\n"
        output += f"🔗 {user.html_url}\n"

        return output
    except Exception as e:
        return f"❌ Erreur: {str(e)}"


print("✅ Fonctions outils créées !")


def github_get_repo_stats(owner: str, repo_name: str) -> str:
    """Statistiques détaillées d'un repository
    Args:
        owner: Propriétaire du repo
        repo_name: Nom du repository
    """
    try:
        g = Github(GITHUB_TOKEN) if GITHUB_TOKEN else Github()
        repo = g.get_repo(f"{owner}/{repo_name}")

        output = f"📊 Statistiques de {repo.full_name}\n\n"
        output += f"⭐ Stars: {repo.stargazers_count:,}\n"
        output += f"🔱 Forks: {repo.forks_count:,}\n"
        output += f"👀 Watchers: {repo.watchers_count:,}\n"
        output += f"📝 Issues ouvertes: {repo.open_issues_count}\n"
        output += f"📅 Créé le: {repo.created_at.strftime('%d/%m/%Y')}\n"
        output += f"🔄 Dernier push: {repo.pushed_at.strftime('%d/%m/%Y')}\n"
        output += f"📦 Taille: {repo.size} KB\n"
        output += f"💻 Langage principal: {repo.language or 'N/A'}\n"
        output += f"📄 Licence: {repo.license.name if repo.license else 'Aucune'}\n"
        output += f"🔗 {repo.html_url}\n"

        return output
    except Exception as e:
        return f"❌ Erreur: {str(e)}"


def github_list_user_repos(username: str, max_results: int = 10) -> str:
    """Liste tous les repositories d'un utilisateur
    Args:
        username: Nom d'utilisateur GitHub
        max_results: Nombre maximum de repos à afficher
    """
    try:
        g = Github(GITHUB_TOKEN) if GITHUB_TOKEN else Github()
        user = g.get_user(username)
        repos = list(user.get_repos()[:max_results])

        output = f"📦 Repositories de {username} ({user.public_repos} public):\n\n"

        for i, repo in enumerate(repos, 1):
            output += f"{i}. {repo.name}\n"
            output += f"   ⭐ {repo.stargazers_count} | 🔱 {repo.forks_count}\n"
            output += f"   💻 {repo.language or 'N/A'}\n"
            output += f"   📝 {repo.description or 'Pas de description'}[:80]\n"
            output += f"   🔗 {repo.html_url}\n\n"

        return output
    except Exception as e:
        return f"❌ Erreur: {str(e)}"


def github_create_issue(owner: str, repo_name: str, title: str, body: str) -> str:
    """Créer une issue dans un repository
    Args:
        owner: Propriétaire du repo
        repo_name: Nom du repository
        title: Titre de l'issue
        body: Description de l'issue
    """
    try:
        g = Github(GITHUB_TOKEN) if GITHUB_TOKEN else Github()
        repo = g.get_repo(f"{owner}/{repo_name}")

        issue = repo.create_issue(title=title, body=body)

        output = f"✅ Issue créée avec succès !\n\n"
        output += f"📌 Titre: {issue.title}\n"
        output += f"🔢 Numéro: #{issue.number}\n"
        output += f"🔗 {issue.html_url}\n"

        return output
    except Exception as e:
        return f"❌ Erreur: {str(e)}"


def github_search_issues(query: str, max_results: int = 5) -> str:
    """Rechercher des issues sur GitHub
    Args:
        query: Mots-clés de recherche
        max_results: Nombre maximum de résultats
    """
    try:
        g = Github(GITHUB_TOKEN) if GITHUB_TOKEN else Github()
        issues = g.search_issues(query=query)

        output = f"🔍 Issues trouvées pour '{query}':\n\n"

        for i, issue in enumerate(list(issues[:max_results]), 1):
            state_emoji = "✅" if issue.state == "closed" else "🔴"
            output += f"{i}. {state_emoji} {issue.title}\n"
            output += f"   📦 Repo: {issue.repository.full_name}\n"
            output += f"   💬 Commentaires: {issue.comments}\n"
            output += f"   🔗 {issue.html_url}\n\n"

        return output
    except Exception as e:
        return f" Erreur: {str(e)}"


def github_trending_repos(language: str = "python", since: str = "weekly") -> str:
    """Repositories tendances (simulation via recherche)
    Args:
        language: Langage de programmation
        since: Période (daily, weekly, monthly)
    """
    try:
        g = Github(GITHUB_TOKEN) if GITHUB_TOKEN else Github()

        # Calculer la date selon la période
        from datetime import datetime, timedelta

        if since == "daily":
            date = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")
        elif since == "monthly":
            date = (datetime.now() - timedelta(days=30)).strftime("%Y-%m-%d")
        else:  # weekly
            date = (datetime.now() - timedelta(days=7)).strftime("%Y-%m-%d")

        query = f"language:{language} created:>{date}"
        repos = g.search_repositories(query=query, sort="stars", order="desc")

        output = f"🔥 Repos {language} tendances ({since}):\n\n"

        for i, repo in enumerate(list(repos[:5]), 1):
            output += f"{i}. {repo.full_name}\n"
            output += f"   ⭐ {repo.stargazers_count:,} stars\n"
            output += f"   📝 {repo.description or 'Pas de description'}[:80]\n"
            output += f"   🔗 {repo.html_url}\n\n"

        return output
    except Exception as e:
        return f" Erreur: {str(e)}"


# ============================================================
# CRÉATION DES AGENTS
# ============================================================
email_agent = Agent(
    model=MODEL_NAME,
    name="email_agent",
    instruction="""You are an Email Management Agent for Gmail.

Your tools:
- gmail_list_emails: List recent emails
- gmail_search_emails: Search emails by keywords
- gmail_send_email: Send emails DIRECTLY (requires: to, subject, body)

CRITICAL - EMAIL SENDING:
- NEVER ask for confirmation before sending
- Send the email IMMEDIATELY when requested
- Extract recipient, subject, and body from user's description
- If any information is missing, ask for it ONCE, then send directly

FORMATTING RULES FOR EMAIL RESPONSES:
You MUST format email listings EXACTLY like this (this is critical for proper display):

1. Subject Line
   De: sender@email.com
   Aperçu: First 100 characters of email...

2. Another Subject
   De: another@email.com
   Aperçu: Email preview text here...

IMPORTANT:
- Number each email (1., 2., 3., etc.)
- Use "De:" (not "From:" or anything else)
- Use "Aperçu:" (not "Preview:" or anything else)
- Keep exact spacing and line breaks as shown
- Include all three lines for each email

Example of correct format:
📧 5 emails récents:

1. Meeting Tomorrow at 3PM
   De: boss@company.com
   Aperçu: Hi team, just a reminder about our meeting tomorrow at 3PM. Please prepare your reports...

2. Project Update Required
   De: colleague@company.com
   Aperçu: Can you send me the latest project status? We need it for the client presentation...

Always provide clear summaries with action items.""",
    tools=[gmail_list_emails, gmail_search_emails, gmail_send_email],
)
email_agent_card = AgentCard(
    name="Email Agent",
    url=f"http://localhost:{EMAIL_AGENT_PORT}",
    description="Manage Gmail: list, search emails",
    version="1.0",
    capabilities=AgentCapabilities(streaming=True),
    default_input_modes=["text/plain"],
    default_output_modes=["text/plain"],
    skills=[
        AgentSkill(
            id="manage_emails",
            name="Manage Emails",
            description="List and search Gmail emails",
            tags=["email", "gmail"],
            examples=["List my recent emails", "Search for emails about meetings"],
        )
    ],
)

remote_email_agent = RemoteA2aAgent(
    name="manage_emails",
    description="Manage Gmail emails",
    agent_card=f"http://localhost:{EMAIL_AGENT_PORT}{AGENT_CARD_WELL_KNOWN_PATH}",
)

print(" Email Agent créé !")
calendar_agent = Agent(
    model=MODEL_NAME,
    name="calendar_agent",
    instruction="""You are a Calendar Management Agent for Google Calendar.

Your tools:
- calendar_list_events: List upcoming events
- calendar_create_event: Create new events
- calendar_delete_event: Delete events
- calendar_check_availability: Check availability for a date

FORMATTING RULES FOR CALENDAR RESPONSES:
You MUST format event listings EXACTLY like this:

1. Event Title
   📅 DD/MM/YYYY à HH:MM

2. Another Event
   📅 DD/MM/YYYY à HH:MM

IMPORTANT:
- Number each event (1., 2., 3., etc.)
- Use the calendar emoji 📅 before the date
- Use French date format: DD/MM/YYYY à HH:MM
- Keep exact spacing and line breaks as shown
- Include both lines for each event

Example of correct format:
📅 5 événements à venir:

1. Team Meeting
   📅 15/12/2024 à 10:00

2. Client Presentation
   📅 16/12/2024 à 14:30

3. Project Review
   📅 18/12/2024 à 09:00

Provide clear event details, suggest meeting times, and handle scheduling conflicts.""",
    tools=[
        calendar_list_events,
        calendar_create_event,
        calendar_delete_event,
        calendar_check_availability,
    ],
)


calendar_agent_card = AgentCard(
    name="Calendar Agent",
    url=f"http://localhost:{CALENDAR_AGENT_PORT}",
    description="Manage Google Calendar events",
    version="1.0",
    capabilities=AgentCapabilities(streaming=True),
    default_input_modes=["text/plain"],
    default_output_modes=["text/plain"],
    skills=[
        AgentSkill(
            id="manage_calendar",
            name="Manage Calendar",
            description="List calendar events",
            tags=["calendar", "events"],
            examples=["Show my calendar", "List upcoming events"],
        )
    ],
)

remote_calendar_agent = RemoteA2aAgent(
    name="manage_calendar",
    description="Manage Google Calendar",
    agent_card=f"http://localhost:{CALENDAR_AGENT_PORT}{AGENT_CARD_WELL_KNOWN_PATH}",
)

print("Calendar Agent créé !")

# ============================================================
#  WEB SEARCH AGENT - INSTRUCTIONS FORMATÉES
# ============================================================

web_search_agent = Agent(
    model=MODEL_NAME,
    name="web_search_agent",
    instruction="""You are a Web Research Agent.

Your tool:
- web_search_tool: Search the web with DuckDuckGo

FORMATTING RULES FOR WEB SEARCH RESPONSES:
You MUST format search results EXACTLY like this:

1. Page Title Here
   🔗 https://example.com/page-url
   Brief description or snippet from the page in about 150 characters...

2. Another Result Title
   🔗 https://another-site.com/article
   Another description or snippet from the search result...

IMPORTANT:
- Number each result (1., 2., 3., etc.)
- Use "🔗" for the URL
- Keep exact spacing and line breaks as shown
- Include ALL THREE lines for each result
- Use the FULL URL (https://...)
- Keep descriptions concise (~150 characters)

Example of correct format:
🔍 Résultats pour: artificial intelligence news

1. Latest AI Breakthroughs in 2024
   🔗 https://techcrunch.com/ai-breakthroughs-2024
   Major advances in AI technology including new language models and breakthrough research in machine learning algorithms...

2. How AI is Transforming Healthcare
   🔗 https://medicalai.com/healthcare-transformation
   Artificial intelligence applications in medical diagnosis, drug discovery, and patient care are revolutionizing the industry...

Provide summaries with top results and actionable insights.""",
    tools=[web_search_tool],
)


web_search_agent_card = AgentCard(
    name="Web Search Agent",
    url=f"http://localhost:{WEB_SEARCH_AGENT_PORT}",
    description="Search the web with DuckDuckGo",
    version="1.0",
    capabilities=AgentCapabilities(streaming=True),
    default_input_modes=["text/plain"],
    default_output_modes=["text/plain"],
    skills=[
        AgentSkill(
            id="search_web",
            name="Search Web",
            description="Search for information online",
            tags=["search", "web"],
            examples=["Search for AI news", "Find Python tutorials"],
        )
    ],
)

remote_web_search_agent = RemoteA2aAgent(
    name="search_web",
    description="Search the web",
    agent_card=f"http://localhost:{WEB_SEARCH_AGENT_PORT}{AGENT_CARD_WELL_KNOWN_PATH}",
)

print(" Web Search Agent créé !")
github_agent = Agent(
    model=MODEL_NAME,
    name="github_agent",
    instruction="""You are a GitHub Management Agent.

Your tools:
- github_search_repos: Search repositories
- github_get_user_info: Get user information
- github_get_repo_stats: Detailed repository statistics
- github_list_user_repos: List all user repositories
- github_create_issue: Create an issue in a repository
- github_search_issues: Search issues across GitHub
- github_trending_repos: Find trending repositories by language

FORMATTING RULES FOR GITHUB REPOSITORY RESPONSES:
You MUST format repository listings EXACTLY like this:

1. owner/repo-name
   ⭐ 1,234 stars
   📝 Repository description here
   🔗 https://github.com/owner/repo-name

2. another-owner/another-repo
   ⭐ 5,678 stars
   📝 Another repository description
   🔗 https://github.com/another-owner/another-repo

IMPORTANT:
- Number each repo (1., 2., 3., etc.)
- Use "⭐" for stars (not just "stars:")
- Use "📝" for description
- Use "🔗" for URL
- Keep exact spacing and line breaks as shown
- Include ALL FOUR lines for each repository
- Use the FULL GitHub URL (https://github.com/...)

Example of correct format:
🐙 Repositories pour: machine learning

1. tensorflow/tensorflow
   ⭐ 185,234 stars
   📝 An Open Source Machine Learning Framework for Everyone
   🔗 https://github.com/tensorflow/tensorflow

2. scikit-learn/scikit-learn
   ⭐ 59,123 stars
   📝 Machine learning in Python
   🔗 https://github.com/scikit-learn/scikit-learn

Provide detailed information with stats, links, and actionable insights.""",
    tools=[
        github_search_repos,
        github_get_user_info,
        github_get_repo_stats,
        github_list_user_repos,
        github_create_issue,
        github_search_issues,
        github_trending_repos,
    ],
)


github_agent_card = AgentCard(
    name="GitHub Agent",
    url=f"http://localhost:{GITHUB_AGENT_PORT}",
    description="Manage GitHub repos and users",
    version="1.0",
    capabilities=AgentCapabilities(streaming=True),
    default_input_modes=["text/plain"],
    default_output_modes=["text/plain"],
    skills=[
        AgentSkill(
            id="manage_github",
            name="Manage GitHub",
            description="Search repos and get user info",
            tags=["github", "repos"],
            examples=["Search ML repositories", "Get user info"],
        )
    ],
)

remote_github_agent = RemoteA2aAgent(
    name="manage_github",
    description="Manage GitHub",
    agent_card=f"http://localhost:{GITHUB_AGENT_PORT}{AGENT_CARD_WELL_KNOWN_PATH}",
)

print("GitHub Agent créé !")


# ============================================================
#  AGENT CONVERSATIONAL
# ============================================================

CONVERSATIONAL_AGENT_PORT = 10029


conversational_agent = Agent(
    model=MODEL_NAME,
    name="conversational_agent",
    instruction="""You are a Conversational Assistant that provides rich, helpful interactions.

PRINCIPLES:
- Be conversational, friendly, and proactive
- Explain what you're doing and why
- Suggest follow-up actions and optimizations
- Handle errors gracefully with alternatives
- Ask clarifying questions when needed
- Use markdown for rich formatting (bold, lists, code blocks)
- Provide context and reasoning for your suggestions

CAPABILITIES:
- Analyze user requests and provide insights
- Suggest workflows and automations
- Help troubleshoot issues
- Provide tips and best practices
- Coordinate multiple tasks

FORMAT AWARENESS:
When discussing emails, calendar events, GitHub repos, or web results, 
respect the formatting patterns used by other agents:
- Numbered lists (1., 2., 3.)
- Consistent emoji usage (📧, 📅, ⭐, 🔗)
- Proper line spacing and structure

Always be helpful and add value beyond just answering questions.""",
    tools=[],
)

conversational_agent_card = AgentCard(
    name="Conversational Agent",
    url=f"http://localhost:{CONVERSATIONAL_AGENT_PORT}",
    description="Friendly assistant for rich interactions",
    version="1.0",
    capabilities=AgentCapabilities(streaming=True),
    default_input_modes=["text/plain"],
    default_output_modes=["text/plain"],
    skills=[
        AgentSkill(
            id="assist_user",
            name="Assist User",
            description="Provide helpful, conversational assistance",
            tags=["conversation", "help"],
            examples=[
                "Explain my schedule",
                "Help me organize tasks",
                "What should I focus on?",
            ],
        )
    ],
)

remote_conversational_agent = RemoteA2aAgent(
    name="assist_user",
    description="Conversational assistant",
    agent_card=f"http://localhost:{CONVERSATIONAL_AGENT_PORT}{AGENT_CARD_WELL_KNOWN_PATH}",
)

print("Conversational Agent créé !")

orchestrator_agent = Agent(
    model=MODEL_NAME,
    name="orchestrator_agent",
    instruction="""You are an AI Orchestrator managing specialized agents.

AVAILABLE AGENTS:
1. Email Agent - Gmail operations (list, search, send)
2. Calendar Agent - Google Calendar (list, create, delete, check availability)
3. Web Search Agent - Web search with DuckDuckGo
4. GitHub Agent - GitHub repos/users management
5. Conversational Agent - Rich interactions and assistance

CRITICAL FORMATTING REQUIREMENTS:
When delegating to agents, YOU MUST ENSURE they return data in the correct format:

FOR EMAILS (Email Agent):
1. Subject
   De: sender@email.com
   Aperçu: Preview text...

FOR CALENDAR (Calendar Agent):
1. Event Title
   📅 DD/MM/YYYY à HH:MM

FOR GITHUB (GitHub Agent):
1. owner/repo-name
   ⭐ stars count
   📝 Description
   🔗 https://github.com/owner/repo

FOR WEB SEARCH (Web Search Agent):
1. Page Title
   🔗 https://url.com
   Description text...

WORKFLOW:
- Analyze user requests carefully
- Delegate to appropriate agent(s)
- VERIFY the response format matches the required pattern
- If format is incorrect, reformat it yourself
- Combine results when needed
- Provide clear, formatted responses
- Suggest next actions

Be intelligent about routing and ALWAYS ensure proper formatting for the frontend display.""",
    sub_agents=[
        remote_email_agent,
        remote_calendar_agent,
        remote_web_search_agent,
        remote_github_agent,
        remote_conversational_agent,
    ],
)
print(" Orchestrator Agent créé !")

orchestrator_agent_card = AgentCard(
    name="Orchestrator Agent",
    url=f"http://localhost:{ORCHESTRATOR_AGENT_PORT}",
    description="Orchestrates all agents",
    version="1.0",
    capabilities=AgentCapabilities(streaming=True),
    default_input_modes=["text/plain"],
    default_output_modes=["text/plain"],
    skills=[
        AgentSkill(
            id="orchestrate",
            name="Orchestrate",
            description="Coordinate multiple agents",
            tags=["orchestration"],
            examples=["Check emails and calendar", "Search and find repos"],
        )
    ],
)

# ============================================================
# SERVEURS A2A
# ============================================================


def create_agent_a2a_server(agent, agent_card):
    """Créer un serveur A2A pour un agent"""
    runner = Runner(
        app_name=agent.name,
        agent=agent,
        artifact_service=InMemoryArtifactService(),
        session_service=InMemorySessionService(),
        memory_service=InMemoryMemoryService(),
    )

    config = A2aAgentExecutorConfig()
    executor = A2aAgentExecutor(runner=runner, config=config)

    request_handler = DefaultRequestHandler(
        agent_executor=executor,
        task_store=InMemoryTaskStore(),
    )

    return A2AStarletteApplication(agent_card=agent_card, http_handler=request_handler)


servers = []


async def run_server_notebook(create_agent_function, port):
    """Lancer un serveur"""
    try:
        print(f"Starting agent on port {port}...")
        app = create_agent_function()
        config = uvicorn.Config(
            app.build(), host="127.0.0.1", port=port, log_level="error", loop="asyncio"
        )
        server = uvicorn.Server(config)
        servers.append(server)
        await server.serve()
    except Exception as e:
        print(f" Error: {e}")


def run_agent_in_background(create_agent_function, port, name):
    """Lancer un agent en arrière-plan"""

    def run():
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            loop.run_until_complete(run_server_notebook(create_agent_function, port))
        except Exception as e:
            print(f" {name} error: {e}")

    thread = threading.Thread(target=run, daemon=True)
    thread.start()
    return thread


print(" Fonctions serveur créées !")

# ============================================================
# CLIENT A2A
# ============================================================


class A2ASimpleClient:
    def __init__(self, default_timeout: float = 3600.0):
        self._agent_info_cache = {}
        self.default_timeout = default_timeout

    async def create_task(self, agent_url: str, message: str) -> str:
        """Envoyer un message à un agent"""
        timeout_config = httpx.Timeout(
            timeout=self.default_timeout,
            connect=10.0,
            read=self.default_timeout,
            write=10.0,
            pool=5.0,
        )

        async with httpx.AsyncClient(timeout=timeout_config) as httpx_client:
            if (
                agent_url in self._agent_info_cache
                and self._agent_info_cache[agent_url]
            ):
                agent_card_data = self._agent_info_cache[agent_url]
            else:
                agent_card_response = await httpx_client.get(
                    f"{agent_url}{AGENT_CARD_WELL_KNOWN_PATH}"
                )
                agent_card_data = self._agent_info_cache[agent_url] = (
                    agent_card_response.json()
                )

            agent_card = AgentCard(**agent_card_data)
            client = A2AClient(httpx_client=httpx_client, agent_card=agent_card)

            send_message_payload = {
                "message": {
                    "role": "user",
                    "parts": [{"kind": "text", "text": message}],
                    "messageId": uuid.uuid4().hex,
                }
            }

            request = SendMessageRequest(
                id=str(uuid.uuid4()), params=MessageSendParams(**send_message_payload)
            )

            response = await client.send_message(request)

            try:
                response_dict = response.model_dump(mode="json", exclude_none=True)

                if "result" in response_dict and "artifacts" in response_dict["result"]:
                    artifacts = response_dict["result"]["artifacts"]
                    for artifact in artifacts:
                        if "parts" in artifact:
                            for part in artifact["parts"]:
                                if "text" in part:
                                    return part["text"]

                return json.dumps(response_dict, indent=2)

            except Exception as e:
                print(f" Erreur parsing: {e}")
                return str(response)


a2a_client = A2ASimpleClient()
print("Client A2A créé !")

# ============================================================
# DÉMARRAGE DES AGENTS
# ============================================================

print("\n🚀 Démarrage des agents...")
run_agent_in_background(
    lambda: create_agent_a2a_server(email_agent, email_agent_card),
    EMAIL_AGENT_PORT,
    "Email",
)
run_agent_in_background(
    lambda: create_agent_a2a_server(calendar_agent, calendar_agent_card),
    CALENDAR_AGENT_PORT,
    "Calendar",
)
run_agent_in_background(
    lambda: create_agent_a2a_server(web_search_agent, web_search_agent_card),
    WEB_SEARCH_AGENT_PORT,
    "Web Search",
)
run_agent_in_background(
    lambda: create_agent_a2a_server(github_agent, github_agent_card),
    GITHUB_AGENT_PORT,
    "GitHub",
)
run_agent_in_background(
    lambda: create_agent_a2a_server(orchestrator_agent, orchestrator_agent_card),
    ORCHESTRATOR_AGENT_PORT,
    "Orchestrator",
)
run_agent_in_background(
    lambda: create_agent_a2a_server(conversational_agent, conversational_agent_card),
    CONVERSATIONAL_AGENT_PORT,
    "Conversational",
)

time.sleep(15)
print("Tous les agents sont prêts !\n")



a2a_client = A2ASimpleClient()
print("Client A2A créé !")

# ============================================================
# API FLASK
# ============================================================


app = Flask(__name__)
CORS(app)


@app.route("/api/chat", methods=["POST"])
def chat():
    """Endpoint pour envoyer des messages à l'orchestrateur"""
    try:
        data = request.get_json()
        message = data.get("message", "")

        if not message:
            return jsonify({"error": "Message vide"}), 400

        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        response = loop.run_until_complete(
            a2a_client.create_task(
                f"http://localhost:{ORCHESTRATOR_AGENT_PORT}", message
            )
        )
        loop.close()

        return jsonify({"success": True, "response": response})

    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@app.route("/api/health", methods=["GET"])
def health():
    """Vérifier que l'API est opérationnelle"""
    return jsonify({"status": "ok", "agents": "running"})


@app.route("/")
def index():
    """Page d'accueil avec interface moderne"""
    return """
<!DOCTYPE html>
<html lang="fr">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Système Multi-Agent</title>
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');
        
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }

      body {
    font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
    background: #0a0a0a;
    height: 100vh;  /* Ajouter cette ligne */
    display: flex;
    padding: 20px;
    color: #e5e5e5;
    overflow: hidden;  /* Ajouter cette ligne */
}

/* Modifier le container */
.container {
    display: flex;
    gap: 20px;
    width: 100%;
    max-width: 1600px;
    margin: 0 auto;
    height: 100%;  /* Ajouter cette ligne */
}

/* Modifier la sidebar */
.sidebar {
    width: 280px;
    background: #1a1a1a;
    border: 1px solid #2a2a2a;
    border-radius: 12px;
    padding: 24px;
    display: flex;
    flex-direction: column;
    gap: 24px;
    height: fit-content;  /* Ajouter cette ligne */
    max-height: 100%;  /* Ajouter cette ligne */
    overflow-y: auto;  /* Ajouter cette ligne */
}

        .sidebar-header {
            padding-bottom: 20px;
            border-bottom: 1px solid #2a2a2a;
        }

        .sidebar-header h2 {
            font-size: 14px;
            font-weight: 600;
            color: rgba(255, 255, 255, 0.9);
            margin-bottom: 12px;
            text-transform: uppercase;
            letter-spacing: 1px;
        }

        .status-badge {
            display: inline-flex;
            align-items: center;
            gap: 8px;
            padding: 8px 12px;
            background: rgba(74, 222, 128, 0.1);
            border: 1px solid rgba(74, 222, 128, 0.2);
            color: #4ade80;
            border-radius: 6px;
            font-size: 12px;
            font-weight: 500;
        }

        .status-dot {
            width: 6px;
            height: 6px;
            background: #4ade80;
            border-radius: 50%;
            animation: pulse 2s infinite;
        }

        @keyframes pulse {
            0%, 100% { opacity: 1; transform: scale(1); }
            50% { opacity: 0.5; transform: scale(0.95); }
        }

        .agent-section h3 {
            font-size: 11px;
            font-weight: 600;
            color: rgba(255, 255, 255, 0.5);
            text-transform: uppercase;
            letter-spacing: 1px;
            margin-bottom: 16px;
        }

        .agent-card {
            background: rgba(255, 255, 255, 0.03);
            border: 1px solid rgba(255, 255, 255, 0.08);
            border-radius: 8px;
            padding: 14px;
            margin-bottom: 10px;
            transition: all 0.2s ease;
            cursor: pointer;
        }

        .agent-card:hover {
            background: rgba(255, 255, 255, 0.06);
            border-color: rgba(255, 255, 255, 0.15);
        }

        .agent-card.active {
            background: rgba(255, 255, 255, 0.08);
            border-color: rgba(255, 255, 255, 0.2);
        }

        .agent-header {
            display: flex;
            align-items: center;
            gap: 12px;
        }

        .agent-icon {
            width: 32px;
            height: 32px;
            background: rgba(255, 255, 255, 0.05);
            border: 1px solid rgba(255, 255, 255, 0.1);
            border-radius: 6px;
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 16px;
            filter: grayscale(100%);
            opacity: 0.8;
        }

        .agent-card:hover .agent-icon {
            opacity: 1;
        }

        .agent-name {
            font-weight: 500;
            font-size: 13px;
            color: rgba(255, 255, 255, 0.9);
        }

        .agent-status {
            display: flex;
            align-items: center;
            gap: 6px;
            font-size: 11px;
            margin-top: 10px;
            color: rgba(255, 255, 255, 0.5);
        }

        .agent-status-dot {
            width: 5px;
            height: 5px;
            background: #4ade80;
            border-radius: 50%;
        }

        /* MAIN CHAT */
   .main-content {
    flex: 1;
    background: #1a1a1a;
    border: 1px solid #2a2a2a;
    border-radius: 12px;
    display: flex;
    flex-direction: column;
    overflow: hidden;
    height: 100%;  /* Ajouter cette ligne */
}

        .chat-header {
            background: rgba(255, 255, 255, 0.02);
            border-bottom: 1px solid #2a2a2a;
            padding: 24px 30px;
            display: flex;
            align-items: center;
            justify-content: space-between;
        }

        .chat-header-left h1 {
            font-size: 18px;
            font-weight: 600;
            margin-bottom: 6px;
            color: rgba(255, 255, 255, 0.9);
        }

        .chat-header-left p {
            color: rgba(255, 255, 255, 0.5);
            font-size: 13px;
        }

        .header-actions {
            display: flex;
            gap: 10px;
        }

        .header-btn {
            padding: 8px 16px;
            background: rgba(255, 255, 255, 0.05);
            border: 1px solid rgba(255, 255, 255, 0.1);
            border-radius: 6px;
            color: rgba(255, 255, 255, 0.8);
            font-weight: 500;
            cursor: pointer;
            transition: all 0.2s;
            font-size: 12px;
        }

        .header-btn:hover {
            background: rgba(255, 255, 255, 0.08);
            border-color: rgba(255, 255, 255, 0.2);
        }

      .chat-messages {
    flex: 1;
    overflow-y: auto;
    padding: 30px;
    background: #0f0f0f;
    min-height: 0;  /* Ajouter cette ligne - important pour le flex */
}

        .message {
            display: flex;
            gap: 14px;
            margin-bottom: 20px;
            animation: slideIn 0.3s ease;
        }

        @keyframes slideIn {
            from {
                opacity: 0;
                transform: translateY(10px);
            }
            to {
                opacity: 1;
                transform: translateY(0);
            }
        }

        .message-avatar {
            width: 36px;
            height: 36px;
            border-radius: 8px;
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 18px;
            flex-shrink: 0;
            background: rgba(255, 255, 255, 0.05);
            border: 1px solid rgba(255, 255, 255, 0.1);
            filter: grayscale(100%);
            opacity: 0.8;
        }

        .message-content {
            flex: 1;
            background: rgba(255, 255, 255, 0.03);
            border: 1px solid rgba(255, 255, 255, 0.08);
            padding: 16px;
            border-radius: 8px;
            max-width: 80%;
        }

        .message.user .message-content {
            background: rgba(255, 255, 255, 0.06);
            border-color: rgba(255, 255, 255, 0.12);
        }

        .message-meta {
            display: flex;
            align-items: center;
            gap: 8px;
            margin-bottom: 8px;
            font-size: 11px;
            font-weight: 500;
            color: rgba(255, 255, 255, 0.5);
            text-transform: uppercase;
            letter-spacing: 0.5px;
        }

        .message-text {
            line-height: 1.6;
            color: rgba(255, 255, 255, 0.85);
            white-space: pre-wrap;
            font-size: 14px;
        }

        /* QUICK ACTIONS */
        .quick-actions {
            padding: 20px 30px;
            background: rgba(255, 255, 255, 0.01);
            border-top: 1px solid #2a2a2a;
            border-bottom: 1px solid #2a2a2a;
        }

        .quick-actions-label {
            font-size: 11px;
            font-weight: 600;
            color: rgba(255, 255, 255, 0.5);
            margin-bottom: 12px;
            text-transform: uppercase;
            letter-spacing: 0.5px;
        }

        .quick-actions-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 10px;
        }

        .quick-action-btn {
            padding: 12px 16px;
            background: rgba(255, 255, 255, 0.03);
            border: 1px solid rgba(255, 255, 255, 0.08);
            border-radius: 6px;
            font-size: 12px;
            cursor: pointer;
            transition: all 0.2s;
            text-align: left;
            display: flex;
            align-items: center;
            gap: 10px;
            font-weight: 400;
            color: rgba(255, 255, 255, 0.7);
        }

        .quick-action-btn:hover {
            border-color: rgba(255, 255, 255, 0.15);
            background: rgba(255, 255, 255, 0.06);
            color: rgba(255, 255, 255, 0.9);
        }

        .quick-action-icon {
            filter: grayscale(100%);
            opacity: 0.6;
        }

        .quick-action-btn:hover .quick-action-icon {
            opacity: 0.9;
        }

        /* INPUT */
        .chat-input-container {
            padding: 20px 30px;
            background: rgba(255, 255, 255, 0.01);
        }

        .input-wrapper {
            display: flex;
            gap: 10px;
            background: rgba(255, 255, 255, 0.03);
            padding: 6px;
            border-radius: 8px;
            border: 1px solid rgba(255, 255, 255, 0.08);
            transition: all 0.2s;
        }

        .input-wrapper:focus-within {
            border-color: rgba(255, 255, 255, 0.15);
            background: rgba(255, 255, 255, 0.05);
        }

        #messageInput {
            flex: 1;
            padding: 10px 14px;
            border: none;
            background: transparent;
            font-size: 14px;
            outline: none;
            font-family: inherit;
            color: rgba(255, 255, 255, 0.9);
        }

        #messageInput::placeholder {
            color: rgba(255, 255, 255, 0.4);
        }

        #sendButton {
            padding: 10px 24px;
            background: rgba(255, 255, 255, 0.1);
            color: rgba(255, 255, 255, 0.9);
            border: 1px solid rgba(255, 255, 255, 0.15);
            border-radius: 6px;
            cursor: pointer;
            font-weight: 500;
            transition: all 0.2s;
            display: flex;
            align-items: center;
            gap: 8px;
            font-size: 13px;
        }

        #sendButton:hover:not(:disabled) {
            background: rgba(255, 255, 255, 0.15);
            border-color: rgba(255, 255, 255, 0.25);
        }

        #sendButton:disabled {
            opacity: 0.4;
            cursor: not-allowed;
        }

        .loading {
            display: flex;
            align-items: center;
            gap: 12px;
            padding: 14px;
            background: rgba(255, 255, 255, 0.03);
            border: 1px solid rgba(255, 255, 255, 0.08);
            border-radius: 8px;
            margin-bottom: 20px;
        }

        .loading-spinner {
            width: 16px;
            height: 16px;
            border: 2px solid rgba(255, 255, 255, 0.1);
            border-top-color: rgba(255, 255, 255, 0.6);
            border-radius: 50%;
            animation: spin 1s linear infinite;
        }

        @keyframes spin {
            to { transform: rotate(360deg); }
        }

        .loading-text {
            color: rgba(255, 255, 255, 0.6);
            font-size: 13px;
        }

        /* SCROLLBAR */
        .chat-messages::-webkit-scrollbar {
            width: 6px;
        }

        .chat-messages::-webkit-scrollbar-track {
            background: transparent;
        }

        .chat-messages::-webkit-scrollbar-thumb {
            background: rgba(255, 255, 255, 0.1);
            border-radius: 3px;
        }

        .chat-messages::-webkit-scrollbar-thumb:hover {
            background: rgba(255, 255, 255, 0.15);
        }

        /* STATS BAR */
        .stats-bar {
            padding: 16px 24px;
            background: rgba(255, 255, 255, 0.02);
            border-top: 1px solid #2a2a2a;
            display: flex;
            justify-content: space-between;
            align-items: center;
        }

        .stat-item {
            display: flex;
            align-items: center;
            gap: 8px;
            font-size: 11px;
            color: rgba(255, 255, 255, 0.5);
        }

        .stat-value {
            color: rgba(255, 255, 255, 0.8);
            font-weight: 600;
        }
    </style>
</head>
<body>
    <div class="container">
        <!-- SIDEBAR -->
        <div class="sidebar">
            <div class="sidebar-header">
                <h2>Contrôle Agents</h2>
                <div class="status-badge">
                    <div class="status-dot"></div>
                    Tous en ligne
                </div>
            </div>

            <div class="agent-section">
                <h3>Statut des Agents</h3>
                
                <div class="agent-card active">
                    <div class="agent-header">
                        <div class="agent-icon">🎯</div>
                        <div class="agent-name">Orchestrateur</div>
                    </div>
                    <div class="agent-status">
                        <div class="agent-status-dot"></div>
                        Port 10028
                    </div>
                </div>

                <div class="agent-card">
                    <div class="agent-header">
                        <div class="agent-icon">📧</div>
                        <div class="agent-name">Email Agent</div>
                    </div>
                    <div class="agent-status">
                        <div class="agent-status-dot"></div>
                        Port 10024
                    </div>
                </div>

                <div class="agent-card">
                    <div class="agent-header">
                        <div class="agent-icon">📅</div>
                        <div class="agent-name">Calendar Agent</div>
                    </div>
                    <div class="agent-status">
                        <div class="agent-status-dot"></div>
                        Port 10025
                    </div>
                </div>

                <div class="agent-card">
                    <div class="agent-header">
                        <div class="agent-icon">🔍</div>
                        <div class="agent-name">Web Search</div>
                    </div>
                    <div class="agent-status">
                        <div class="agent-status-dot"></div>
                        Port 10026
                    </div>
                </div>

                <div class="agent-card">
                    <div class="agent-header">
                        <div class="agent-icon">🐙</div>
                        <div class="agent-name">GitHub Agent</div>
                    </div>
                    <div class="agent-status">
                        <div class="agent-status-dot"></div>
                        Port 10027
                    </div>
                </div>

                <div class="agent-card">
                    <div class="agent-header">
                        <div class="agent-icon">💬</div>
                        <div class="agent-name">Conversational</div>
                    </div>
                    <div class="agent-status">
                        <div class="agent-status-dot"></div>
                        Port 10029
                    </div>
                </div>
            </div>

            <div class="stats-bar">
                <div class="stat-item">
                    <span>Requêtes</span>
                    <span class="stat-value" id="requestCount">0</span>
                </div>
                <div class="stat-item">
                    <span>Uptime</span>
                    <span class="stat-value" id="uptime">00:00</span>
                </div>
            </div>
        </div>

        <!-- MAIN CHAT -->
        <div class="main-content">
            <div class="chat-header">
                <div class="chat-header-left">
                    <h1>Système Multi-Agent</h1>
                    <p>Orchestration intelligente de vos agents IA</p>
                </div>
                <div class="header-actions">
                    <button class="header-btn" onclick="clearChat()">🗑️ Effacer</button>
                    <button class="header-btn" onclick="location.reload()">🔄 Refresh</button>
                </div>
            </div>

            <div id="chatContainer" class="chat-messages"></div>

            <div class="quick-actions">
                <div class="quick-actions-label">Actions Rapides</div>
                <div class="quick-actions-grid">
                    <button class="quick-action-btn" onclick="sendExample('Liste mes derniers emails')">
                        <span class="quick-action-icon">📧</span>
                        Mes emails récents
                    </button>
                    <button class="quick-action-btn" onclick="sendExample('Montre mon calendrier aujourd\\'hui')">
                        <span class="quick-action-icon">📅</span>
                        Calendrier aujourd'hui
                    </button>
                    <button class="quick-action-btn" onclick="sendExample('Recherche des repos Python sur GitHub')">
                        <span class="quick-action-icon">🐙</span>
                        Repos Python
                    </button>
                    <button class="quick-action-btn" onclick="sendExample('Actualités sur l\\'IA')">
                        <span class="quick-action-icon">🔍</span>
                        News IA
                    </button>
                    <button class="quick-action-btn" onclick="sendExample('Cherche des tutoriels machine learning')">
                        <span class="quick-action-icon">🔍</span>
                        Tutoriels ML
                    </button>
                </div>
            </div>

            <div class="chat-input-container">
                <div class="input-wrapper">
                    <input 
                        type="text" 
                        id="messageInput" 
                        placeholder="Tapez votre message..."
                        onkeypress="if(event.key==='Enter') sendMessage()"
                    >
                    <button id="sendButton" onclick="sendMessage()">
                        <span>Envoyer</span>
                    </button>
                </div>
            </div>
        </div>
    </div>

    <script>
        const chatContainer = document.getElementById('chatContainer');
        const messageInput = document.getElementById('messageInput');
        const sendButton = document.getElementById('sendButton');
        let requestCount = 0;
        let startTime = Date.now();

        // Update uptime
        setInterval(() => {
            const elapsed = Math.floor((Date.now() - startTime) / 1000);
            const minutes = Math.floor(elapsed / 60);
            const seconds = elapsed % 60;
            document.getElementById('uptime').textContent = 
                `${String(minutes).padStart(2, '0')}:${String(seconds).padStart(2, '0')}`;
        }, 1000);

        function clearChat() {
            chatContainer.innerHTML = '';
            addMessage(`Chat effacé. Comment puis-je vous aider ?`, false);
        }

        function formatResponse(text) {
            // Formater les emails
            text = text.replace(/(\d+)\\.\\s*([^\\n]+)\\n\\s*De:\\s*([^\\n]+)\\n\\s*Aperçu:\\s*([^\\n]+)/g, 
                '<div style="margin: 12px 0; padding: 12px; background: rgba(255,255,255,0.05); border-left: 2px solid rgba(255,255,255,0.2); border-radius: 4px;">' +
                '<div style="font-weight: 600; margin-bottom: 6px;">$2</div>' +
                '<div style="font-size: 12px; color: rgba(255,255,255,0.6); margin-bottom: 4px;">De: $3</div>' +
                '<div style="font-size: 12px; color: rgba(255,255,255,0.5);">$4</div>' +
                '</div>');
            
            // Formater les événements calendrier
            text = text.replace(/(\d+)\\.\\s*([^\\n]+)\\n\\s*📅\\s*([^\\n]+)/g,
                '<div style="margin: 12px 0; padding: 12px; background: rgba(255,255,255,0.05); border-left: 2px solid rgba(74,222,128,0.4); border-radius: 4px;">' +
                '<div style="font-weight: 600; margin-bottom: 4px;">$2</div>' +
                '<div style="font-size: 12px; color: rgba(74,222,128,0.8);">📅 $3</div>' +
                '</div>');
            
            // Formater les repos GitHub
            text = text.replace(/(\d+)\\.\\s*([^\\n]+)\\n\\s*⭐\\s*([^\\n]+)\\n\\s*📝\\s*([^\\n]+)\\n\\s*🔗\\s*([^\\n]+)/g,
                '<div style="margin: 12px 0; padding: 12px; background: rgba(255,255,255,0.05); border-left: 2px solid rgba(255,255,255,0.2); border-radius: 4px;">' +
                '<div style="font-weight: 600; margin-bottom: 6px;">$2</div>' +
                '<div style="font-size: 12px; color: rgba(255,255,255,0.6); margin-bottom: 3px;">⭐ $3</div>' +
                '<div style="font-size: 12px; color: rgba(255,255,255,0.5); margin-bottom: 4px;">$4</div>' +
                '<a href="$5" target="_blank" style="font-size: 11px; color: rgba(74,222,128,0.8); text-decoration: none;">🔗 Voir le repo →</a>' +
                '</div>');
            
            // Formater les résultats web
            text = text.replace(/(\d+)\\.\\s*([^\\n]+)\\n\\s*🔗\\s*([^\\n]+)\\n\\s*([^\\n]+)/g,
                '<div style="margin: 12px 0; padding: 12px; background: rgba(255,255,255,0.05); border-left: 2px solid rgba(255,255,255,0.2); border-radius: 4px;">' +
                '<div style="font-weight: 600; margin-bottom: 6px;">$2</div>' +
                '<a href="$3" target="_blank" style="font-size: 11px; color: rgba(74,222,128,0.8); text-decoration: none; display: block; margin-bottom: 4px;">🔗 $3</a>' +
                '<div style="font-size: 12px; color: rgba(255,255,255,0.5);">$4</div>' +
                '</div>');
            
            return text;
        }

        function addMessage(content, isUser) {
            const messageDiv = document.createElement('div');
            messageDiv.className = `message ${isUser ? 'user' : 'assistant'}`;
            
            const timestamp = new Date().toLocaleTimeString('fr-FR', {
                hour: '2-digit',
                minute: '2-digit'
            });
            
            const formattedContent = isUser ? content : formatResponse(content);
            
            messageDiv.innerHTML = `
                <div class="message-avatar">${isUser ? '👤' : '🤖'}</div>
                <div class="message-content">
                    <div class="message-meta">
                        ${isUser ? 'Vous' : 'Assistant'} • ${timestamp}
                    </div>
                    <div class="message-text">${formattedContent}</div>
                </div>
            `;
            
            chatContainer.appendChild(messageDiv);
            chatContainer.scrollTop = chatContainer.scrollHeight;
        }

        function addLoading() {
            const loadingDiv = document.createElement('div');
            loadingDiv.className = 'loading';
            loadingDiv.id = 'loading';
            loadingDiv.innerHTML = `
                <div class="loading-spinner"></div>
                <span class="loading-text">Traitement en cours...</span>
            `;
            chatContainer.appendChild(loadingDiv);
            chatContainer.scrollTop = chatContainer.scrollHeight;
        }

        function removeLoading() {
            const loading = document.getElementById('loading');
            if (loading) loading.remove();
        }

        async function sendMessage() {
            const message = messageInput.value.trim();
            if (!message) return;

            addMessage(message, true);
            messageInput.value = '';
            sendButton.disabled = true;
            addLoading();
            requestCount++;
            document.getElementById('requestCount').textContent = requestCount;

            try {
                const response = await fetch('/api/chat', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ message })
                });

                const data = await response.json();
                removeLoading();

                if (data.success) {
                    addMessage(data.response, false);
                } else {
                    addMessage('Erreur: ' + data.error, false);
                }
            } catch (error) {
                removeLoading();
                addMessage(' Erreur de connexion: ' + error.message, false);
            } finally {
                sendButton.disabled = false;
                messageInput.focus();
            }
        }

        function sendExample(text) {
            messageInput.value = text;
            sendMessage();
        }

        // Message de bienvenue
        addMessage(`Bienvenue dans le système multi-agents.

Je peux vous assister avec :
• Gestion de vos emails Gmail
• Votre calendrier Google
• Recherches web en temps réel
• Informations GitHub

Que puis-je faire pour vous ?`, false);
    </script>
</body>
</html>
    """


# ============================================================
#  DÉMARRAGE FLASK
# ============================================================

if __name__ == "__main__":
    print("\n" + "=" * 80)
    print("API FLASK DÉMARRÉE")
    print("=" * 80)
    print(f"Interface web: http://localhost:5000")
    print(f"API endpoint: http://localhost:5000/api/chat")
    print(f"Health check: http://localhost:5000/api/health")
    print("=" * 80 + "\n")

    app.run(host="0.0.0.0", port=5000, debug=False)
