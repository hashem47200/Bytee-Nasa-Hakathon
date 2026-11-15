# Software Requirements Specification (SRS)
## NASA Explorer Hub — Space Exploration Educational Platform for Children

---

### 1. Introduction

#### 1.1 Purpose
This Software Requirements Specification (SRS) document details the functional, architectural, database, and security requirements for the **NASA Explorer Hub** educational space platform. The platform teaches children about space exploration missions to Mars and the Moon using interactive 3D visualizations, rich mission stories, and knowledge-check quizzes.

#### 1.2 Scope
The system transitions the platform from a static JSON-file dependent architecture to a normalized, database-driven **Python Django** backend. It integrates user authentication, progress tracking, attempt recording, and server-side evaluation.

---

### 2. Overall Description

#### 2.1 Product Perspective
- **Frontend**: Single-Page Application (SPA) built with HTML5, CSS3 glassmorphism, Three.js 3D planetary rendering, and vanilla JavaScript.
- **Backend**: Python 3 / Django framework providing RESTful JSON APIs and administrative management.
- **Database**: Relational SQLite database using Django ORM.
- **Data Source**: Seed file `missions/fixtures/data.json` migrated into normalized tables with idempotent management command `python manage.py import_missions`.

#### 2.2 User Characteristics
- Primary users are elementary and middle school students (children).
- Interfaces must be engaging, gamified, non-punitive, and child-safe.
- Usernames ("callsigns") are used as explorer identities with XP, badges, and rank advancement.

---

### 3. System Architecture & Database Schema

#### 3.1 Relational Data Model
```
[ Planet ] 1 ──< * [ Vehicle ] 1 ──< * [ Story ]
                        │
                        ├────< * [ VehicleImage ]
                        │
                        └────< * [ Question ] 1 ──< * [ Answer ]
                                      ▲
                                      │
[ User ] 1 ──── 1 [ UserProgress ]    │
    │                                 │
    └──────────< * [ QuestionAttempt ]┘
```

#### 3.2 Entities & Fields
1. **`Planet`**:
   - `id`: AutoField
   - `name`: CharField (e.g. "Mars", "Moon")
   - `slug`: SlugField (unique, indexed)
   - `description`: TextField
   - `texture_image`: CharField
   - `is_active`: BooleanField 

2. **`Vehicle`**:
   - `id`: IntegerField (Primary Key, preserving canonical IDs 1..6) 
   - `planet`: ForeignKey(`Planet`, on_delete=CASCADE) 
   - `code`: CharField (e.g. "M-4", "M-0") 
   - `name`: CharField (e.g. "Mars Pathfinder", "Apollo 11 Eagle") 
   - `launch_date`: DateField 
   - `landing_date`: DateField 
   - `coordinates`: CharField (e.g. "19.13°N, 33.22°W") 
   - `image_path`: CharField 
   - `order`: PositiveIntegerField 

3. **`Story`**:
   - `id`: AutoField
   - `vehicle`: ForeignKey(`Vehicle`, on_delete=CASCADE)
   - `title`: CharField
   - `content`: TextField (First-person mission narrative)
   - `order`: PositiveIntegerField

4. **`VehicleImage`**:
   - `id`: AutoField
   - `vehicle`: ForeignKey(`Vehicle`, on_delete=CASCADE)
   - `image_path`: CharField
   - `caption`: CharField
   - `is_primary`: BooleanField

5. **`Question`**:
   - `id`: AutoField
   - `vehicle`: ForeignKey(`Vehicle`, on_delete=CASCADE)
   - `text`: TextField
   - `order`: PositiveIntegerField

6. **`Answer`**:
   - `id`: AutoField
   - `question`: ForeignKey(`Question`, on_delete=CASCADE)
   - `text`: CharField
   - `is_correct`: BooleanField
   - `order`: PositiveIntegerField

7. **`UserProgress`**:
   - `user`: OneToOneField(`User`, on_delete=CASCADE)
   - `total_questions_answered`: PositiveIntegerField (total attempts submitted)
   - `total_correct_answers`: PositiveIntegerField (total correct attempts)
   - `total_wrong_answers`: PositiveIntegerField (total incorrect attempts)
   - `last_activity`: DateTimeField
   - *Calculated properties*: `unique_questions_answered`, `unique_questions_solved`, `accuracy_rate`

8. **`QuestionAttempt`**:
   - `user`: ForeignKey(`User`, on_delete=CASCADE)
   - `question`: ForeignKey(`Question`, on_delete=CASCADE)
   - `selected_answer`: ForeignKey(`Answer`, on_delete=SET_NULL, null=True)
   - `selected_text`: CharField
   - `is_correct`: BooleanField
   - `attempted_at`: DateTimeField (indexed)

---

### 4. Functional Requirements

#### 4.1 Data Migration
- **FR-1.1**: The system must provide a command `python manage.py import_missions` to import `missions/fixtures/data.json`.
- **FR-1.2**: Running the command multiple times must be idempotent without creating duplicate records.
- **FR-1.3**: The original `data.json` must remain intact and unmodified.

#### 4.2 Authentication & Authorization
- **FR-2.1**: Registration requires `username`, `email`, and `password`.
- **FR-2.2**: Usernames must be unique (case-insensitive).
- **FR-2.3**: Passwords must be hashed using Django PBKDF2; plain-text passwords must never be stored.
- **FR-2.4**: Session-based login and logout via secure endpoints.

#### 4.3 Educational Content Delivery
- **FR-3.1**: Public endpoints provide planets, vehicles, and stories.
- **FR-3.2**: Questions endpoint must **never** expose `is_correct` or `correct_answer` before an answer is submitted.
- **FR-3.3**: The canonical `/data.json` endpoint dynamically serves data from the database for full backward compatibility.

#### 4.4 Quiz Submission & Achievement Tracking
- **FR-4.1**: Answers submitted to `/api/submit-answer/` are verified server-side against the database.
- **FR-4.2**: Client-supplied correctness indicators are rejected.
- **FR-4.3**: Each submission increments `total_questions_answered`, and either `total_correct_answers` or `total_wrong_answers`.
- **FR-4.4**: Users are free to retry questions even after wrong answers.
- **FR-4.5**: Accidental rapid duplicate submissions (retries within 4s with the identical answer) are debounced and not double-counted.
- **FR-4.6**: Database transactions use `select_for_update()` to prevent counter corruption during concurrent requests.

---

### 5. API Specification

| Endpoint | Method | Auth Required | Description |
| :--- | :---: | :---: | :--- |
| `GET /` | GET | No | Serves main single-page application (`index.html`) |
| `GET /data.json` | GET | No | Backward-compatible full mission dataset from DB |
| `GET /api/auth/csrf/` | GET | No | Retrieves CSRF token and sets cookie |
| `POST /api/auth/register/` | POST | No | Registers new cadet (`username`, `email`, `password`) |
| `POST /api/auth/login/` | POST | No | Authenticates cadet session |
| `POST /api/auth/logout/` | POST | Yes | Terminates cadet session |
| `GET /api/auth/me/` | GET | No/Yes | Current session status and safe user profile |
| `GET /api/planets/` | GET | No | List of active planets |
| `GET /api/planets/<identifier>/vehicles/` | GET | No | Vehicles belonging to a planet |
| `GET /api/vehicles/<id>/story/` | GET | No | Mission narrative sections for a vehicle |
| `GET /api/vehicles/<id>/questions/` | GET | No | Questions & choices (answers hidden) |
| `POST /api/submit-answer/` | POST | Optional | Submits answer, evaluates, records attempt |
| `GET /api/user/achievements/` | GET | Yes | Ranks, XP, badges, and unlockable diploma |
| `GET /api/user/progress/` | GET | Yes | Total attempts, accuracy, solved mission IDs |

---

### 6. Non-Functional & Security Requirements

1. **Child Data Safety**:
   - Email addresses are strictly hidden from public endpoints and never rendered client-side for other users.
   - User progress records are isolated per user.
2. **Concurrency & Atomicity**:
   - `transaction.atomic()` with row-level locks ensures counters are never corrupted by race conditions.
3. **Resilience & Fallback**:
   - The frontend gracefully falls back to embedded data if running completely offline, while automatically connecting to the Django API when online.
