# Semantic Search Extension - Refactoring Summary

## Overview
The Semantic Search Extension has been refactored to implement a **4-Layer Cognitive Architecture** with an Agent orchestrator.

## Architecture

### Cognitive Layers

#### 1. **PERCEPTION Layer** (`backend/app/services/perception/`)
- **Purpose**: Context understanding and routing
- **Responsibilities**:
  - Analyzes user queries to determine intent
  - Categorizes content (Sports, Politics, Financial, Health & Medical, Current Affairs, Technology, Others)
  - Extracts keywords from queries
  - Calculates relevance scores based on user preferences
  - Uses Nomic embedding model for semantic understanding

#### 2. **MEMORY Layer** (`backend/app/services/memory/`)
- **Purpose**: Stores and retrieves information
- **Responsibilities**:
  - **Long-term Memory**: FAISS index for persistent semantic search
  - **Short-term Memory**: In-memory storage for recent context (1 hour timeout)
  - **User Preferences Storage**: JSON file storage for user settings
  - Filters results based on user preferences
  - Skips confidential sites based on user preference

#### 3. **DECISION-MAKING Layer** (`backend/app/services/decision/`)
- **Purpose**: Plans actions and categorizes content
- **Responsibilities**:
  - Determines what actions to take (search, highlight, categorize, favorite)
  - Categorizes content based on keywords and user preferences
  - Scores results based on relevance and user preferences
  - Applies filtering rules (confidential sites, categories)
  - Prioritizes actions

#### 4. **ACTION Layer** (`backend/app/services/action/`)
- **Purpose**: Executes decided actions
- **Responsibilities**:
  - Executes search operations
  - Applies highlighting to search terms
  - Categorizes search results
  - Manages favorites functionality
  - Returns formatted results

### Agent Orchestrator (`backend/app/agent/`)
- **Purpose**: Main orchestrator that coordinates all cognitive layers
- **Flow**: 
  ```
  User Query → Agent → Perception → Memory → Decision → Action → Results
  ```

## System Prompts
All system prompts are stored in `backend/app/config/system_prompts.json` with support for personalization parameters.

## New Features

### 1. User Preferences
- **Location**: Preferences tab in popup
- **Fields**:
  - Interests
  - Location
  - Favorite Topics
  - Taste/Preferences
- **Options**:
  - Highlight search terms (checkbox)
  - Categorize search results (checkbox)
  - Skip confidential sites (checkbox)
- **Preferred Categories**: Multi-select checkboxes for Sports, Politics, Financial, Health & Medical, Current Affairs, Technology, Others

### 2. Favorites System
- **Location**: Favorites tab in popup
- **Features**:
  - Add search results to favorites
  - View all favorites
  - Remove favorites
  - Favorites stored in user preferences JSON file

### 3. Search Enhancement
- Search queries now use cognitive agent
- User preferences are automatically applied
- Results are personalized based on user context
- Automatic categorization if enabled
- Confidential site filtering based on preferences

## File Structure Changes

### New Files Created:
```
backend/app/
├── agent/
│   ├── __init__.py
│   └── cognitive_agent.py
├── config/
│   ├── __init__.py
│   └── system_prompts.json
├── services/
│   ├── perception/
│   │   ├── __init__.py
│   │   └── perception_layer.py
│   ├── memory/
│   │   ├── __init__.py
│   │   └── memory_layer.py
│   ├── decision/
│   │   ├── __init__.py
│   │   └── decision_layer.py
│   └── action/
│       ├── __init__.py
│       └── action_layer.py
```

### Modified Files:
- `backend/app/api/routes.py` - Added new API endpoints for preferences, favorites, categorization
- `popup.html` - Added Preferences and Favorites tabs
- `popup.js` - Added preferences management, favorites functionality, category checkboxes
- `background.js` - Updated to pass user context to backend

## API Endpoints

### New Endpoints:
- `GET /api/preferences` - Get user preferences
- `POST /api/preferences` - Update user preferences
- `GET /api/favorites` - Get favorites list
- `POST /api/favorites` - Add to favorites
- `DELETE /api/favorites` - Remove from favorites
- `POST /api/categorize` - Categorize content

### Modified Endpoints:
- `POST /api/search` - Now uses cognitive agent with user context

## Usage

### 1. Setting User Preferences
1. Open the extension popup
2. Go to "Preferences" tab
3. Fill in your interests, location, favorite topics, taste
4. Select search options (highlight, categorize, skip confidential)
5. Select preferred categories
6. Click "Save Preferences"

### 2. Adding Favorites
1. Perform a search
2. Click "Add to Favorites" button on any result
3. View favorites in "Favorites" tab

### 3. Searching with Context
- Search automatically uses your preferences
- Results are filtered by selected categories
- Confidential sites are skipped if enabled
- Results are personalized based on interests and topics

## Benefits

1. **Personalization**: Search results adapt to user preferences
2. **Modularity**: Each cognitive layer is separate and testable
3. **Extensibility**: Easy to add new features or modify behavior
4. **Maintainability**: Clear separation of concerns
5. **User Control**: Fine-grained control over search behavior

## Technical Details

### Memory Management
- Long-term: FAISS index (persistent)
- Short-term: In-memory with 1-hour timeout
- User preferences: JSON file (`backend/data/user_preferences.json`)

### Categorization
- Keyword-based detection
- 7 categories: Sports, Politics, Financial, Health & Medical, Current Affairs, Technology, Others

### Confidential Sites
- Pattern-based matching
- Configurable in Settings tab
- Filtered out if user preference enabled

## Future Enhancements
- LLM-based categorization instead of keyword matching
- Learning from user behavior to improve preferences
- Advanced scoring algorithms
- Multi-language support
- Export/import preferences

