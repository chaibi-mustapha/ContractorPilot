# ContractorPilot — From Site Visit to Professional Quote with CALL-E 📞🏠

> **Hackathon CALL-E (Devpost)**: *Your Code Is Calling*  
> **Pitch:** ContractorPilot aide les entrepreneurs en aménagement et rénovation à transformer une visite de chantier en devis professionnel optimisé. L'agent vocal autonome **CALL-E** contacte directement fournisseurs et artisans par téléphone, collecte les prix réels, compare les offres avec un score multicritères, et génère un devis final prêt pour le client.

---

## 🌟 Fonctionnalités Clés

1. **Visite Intelligente (Site Visit Capture)** : Métrés précis des pièces (Longueur, Largeur, Hauteur, surfaces utiles) et qualification des travaux par pièce (Salon, Cuisine, Salle de bain).
2. **Décomposition IA des Besoins** : Structuration instantanée en matériaux (m² de carrelage avec coefficient de coupe, litres de peinture 2 couches, spots LED, robinetterie) et jours de main-d'œuvre requis.
3. **AI Call Center CALL-E** :
   - **Mode Réel** : Intégration directe du SDK officiel `calle-ai` (`CalleClient`) pour passer de véritables appels vocaux via l'API CALL-E avec `result_schema` structuré.
   - **Mode Démo Interactif / Sandbox** : Simulateur visuel et audio interactif en temps réel (ondes audio réactives, affichage progressif du transcript dialogue agent/interlocuteur, extraction dynamique des tarifs, stocks et remises) idéal pour les jurys et vidéos de démonstration.
4. **Matrice de Comparaison & Scoring Intelligent** : Score pondéré sur 100 points (40% Prix, 20% Disponibilité, 15% Délai, 10% Livraison, 10% Fiabilité, 5% Remise) avec recommandation automatique de la meilleure combinaison globale.
5. **Studio Devis & Calcul de Marge** : Curseur de marge commerciale entrepreneur (ex: 20%), prise en compte des frais de gestion et taxes, édition d'un devis propre au format N° CP-2026-001 avec bouton d'impression / export PDF direct.

---

## 🛠️ Architecture Technique

- **Backend** : FastAPI (Python 3.13), Uvicorn, WebSockets pour le streaming d'appels, SDK `calle-ai`.
- **Frontend** : Single Page Application responsive Vanilla HTML5/CSS3/JS, thème sombre avec glassmorphism, typographie Outfit/Inter, animations audio waveforms Web Audio API.
- **Stockage** : Persistance JSON / SQLite (`backend/data/renovai_store.json`) pré-chargée avec le cas d'usage complet d'un Appartement F4 de 120 m².

---

## 🚀 Démarrage Rapide

### 1. Prérequis
- Python 3.10+ (Python 3.13 installé et configuré)

### 2. Lancement du serveur
```bash
python run_server.py
```
Puis ouvrez votre navigateur sur : **[http://localhost:8000](http://localhost:8000)**

### 3. Configuration de la Clé CALL-E (Optionnel pour les appels réels)
- Créez un fichier `.env` ou cliquez sur le bouton **⚙️ Config** dans l'en-tête de l'application :
```env
CALLE_API_KEY=votre_cle_api_calle_ici
```

---

## 🎬 Scénario Idéal de Démonstration Vidéo (Hackathon)

1. **Introduction (15s)** : Présentation de la problématique des devis dans le bâtiment (heures perdues au téléphone).
2. **Visite de chantier (30s)** : Visualisation de l'Appartement F4 (120 m²), ajout d'une pièce ou consultation des pièces existantes.
3. **Extraction des besoins (20s)** : Découverte des postes calculés par l'IA (48 m² de carrelage, peinture, électricien, carreleur).
4. **AI Call Center CALL-E (45s)** : Lancement d'un appel en direct vers le *Comptoir Céramique Moderne (Fournisseur B)*, observation des ondes vocales, de la conversation audio et de l'extraction instantanée des données chiffrées (2 650 DA/m², 60 m² dispo, 5% de remise).
5. **Comparateur d'offres (20s)** : Affichage du tableau de scoring avec la sélection recommandée par l'IA.
6. **Devis final (30s)** : Réglage de la marge entrepreneur (20%) et génération du devis final prêt pour le client.
