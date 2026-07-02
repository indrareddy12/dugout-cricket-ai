# PRODUCT PRD & AI AUTOMATION ARCHITECTURE
## Project DugOut: Redefining the Cricket Social Experience

---

| Document Control | Value |
| :--- | :--- |
| **Document Version** | v1.1 (Production-Ready Draft) |
| **Author** | AI Automation Intern |
| **Target Audience** | Engineering Leadership, Head of Product, Senior Stakeholders |
| **Status** | Pending Review |
| **Last Updated** | June 15, 2026 |

---

## 1. Executive Summary & Strategic Vision

### 1.1. The Opportunity Gap
Cricket consumption today is highly fragmented:
*   **Data Platforms (e.g., Cricbuzz, ESPNcricinfo):** Excellent at providing raw data (ball-by-ball scorecards, player histories, partnerships). However, they are static, transactional, and read-only.
*   **Generic Social Networks (e.g., Twitter/X, Reddit, Threads):** Highly active community commentary, but conversations are unstructured, polluted with irrelevant noise, and completely detached from the live match context.

**DugOut** bridges this gap. By building a **data-integrated cricket social network**, DugOut converts passive match viewers into active community participants.

```
+--------------------------------------------------------+
|                      DUGOUT VISION                     |
|                                                        |
|   [ Cricbuzz (Scorecard) ] + [ Twitter/X (Community) ]  |
|                            =                           |
|            [ DugOut: The Interactive Stadium ]         |
+--------------------------------------------------------+
```

### 1.2. Core Business KPIs
To justify development, the proposed features aim to drive:
1.  **Session Duration (Stickiness):** Increase average daily time spent per user from 3 minutes (standard scorecard check) to 25 minutes (live match discussion).
2.  **Daily Active Users / Monthly Active Users (DAU/MAU) Ratio:** Target a >45% ratio by utilizing gamification and notifications during live matches.
3.  **User Retention (D7/D30):** Enhance onboarding personalization to hook users based on their specific team/player preferences.

---

## 2. Comprehensive Feature Specification (Deep Dive)

### 2.1. Feature 1: Contextual Match "Stands" (Tribal Chatrooms)
Instead of a single global chatroom which devolves into spam, DugOut will introduce virtual "Stands" corresponding to matches.

*   **UI/UX Layout:**
    *   **Dual Viewport:** The top 30% of the mobile screen displays the live interactive scorecard (runs, overs, wickets, bowler stats). The bottom 70% features the live chat.
    *   **Stand Selector:** Tabs to switch between **Fan Stands** (e.g., *CSK Stand* vs. *MI Stand*) and a **Neutral Stand** (moderated, data-focused banter).
    
    **UI Mockup Sketch:**
    ```text
    +-------------------------------------------------------+
    | [<-] LIVE: CSK vs MI (T20)                  (Search)   |
    +-------------------------------------------------------+
    |  CSK: 184/4 (18.2 Overs)     |  Target: 192           |
    |  Ruturaj: 76*(42)            |  Bumrah: 3.2-0-28-2    |
    |  Recent: [ 6 ] [ W ] [ 1 ] [ 4 ] [ 0 ] [ 2 ]          |
    +-------------------------------------------------------+
    |  FAN PULSE: CSK [||||||||||||......] MI (62% Excited)  |
    +-------------------------------------------------------+
    |  [ CSK Stand ]      *[ MI Stand ]*     [ Neutral ]    |
    +-------------------------------------------------------+
    | (MI Stand Chat)                                       |
    | [BlueFan99]: Bumrah is bringing us back! Let's go!    |
    | [Mumbai_4_Ever]: Rohit need to launch in second innings|
    | [Duggy_AI_Bot]: Bumrah has historically conceded only  |
    |                 5.4 runs per over in the death.       |
    |                                                       |
    +-------------------------------------------------------+
    | [ Write your message to MI Stand...          ] (Send) |
    +-------------------------------------------------------+
    ```
*   **Technical Implementation Details:**
    *   **WebSockets Channel Architecture:** Separate Redis Pub/Sub channels map to each match stand (`match:id:csk_stand`, `match:id:neutral_stand`).
    *   **State Hydration:** Messages are temporarily cached in Redis (capped at 100 messages) for instant load times, then archived to PostgreSQL in micro-batches to optimize database writes.

---

### 2.2. Feature 2: Moment-Based Event-Triggered Threading
DugOut will automatically group social discussions around the match's turning points rather than running a flat chronological feed.

*   **Workflow:**
    1.  The **Live Score Ingestion Engine** detects a high-impact event (e.g., Wicket, Six, Half-Century, DRS Review).
    2.  An automated background worker triggers the creation of a **Moment Thread** (e.g., `Thread: Dhoni hits a 95m six off Bumrah!`).
    3.  A card for this thread is injected directly into the live feed and pinned to the live ball-by-ball timeline.
    
    **UI Mockup Sketch:**
    ```text
    +-------------------------------------------------------+
    |  [WICKET MOMENT] - OVER 12.4                          |
    |  J. Bumrah bowls V. Kohli (Bowled!)                   |
    |  Kohli: 48 (32b) - MI fans celebrating!                |
    +-------------------------------------------------------+
    |  [DugOut Threads] ----------------------------------- |
    |  [RCB_DieHard]: That ball was unplayable, swung 3     |
    |                 degrees back in!                      |
    |  [CricketGeek]: Kohli's stance was too open. Stumps   |
    |                 shattered.                            |
    |                                                       |
    |  [+] Reply to this wicket moment...                   |
    +-------------------------------------------------------+
    ```
*   **Technical Flow:**

```
[Live Score Feed] ---> [Match Event Parser] ---> (Detects Key Event: e.g., Wicket)
                               |
                               v
                   [Automated Thread Creator]
                               |
                               v
          [Dynamic Feed Injection + Timeline Pinning]
```

---

### 2.3. Feature 3: Audio Dugouts (Interactive Spaces)
Provide live-audio capability directly inside match screens for creators and fan communities.

*   **UI/UX Layout:** A floating mini-player displaying active audio speakers at the bottom of the match page, allowing the user to browse scores and chat rooms simultaneously.
    
    **UI Mockup Sketch:**
    ```text
    +-------------------------------------------------------+
    | [((•)) Audio Dugout: The Death Over Special]          |
    | Host: @VirenderSehwag (Speaking)                      |
    | Speakers: [ @Harbhajan_S ] [ @GautamG ] [@Fanatic99]  |
    | Listeners: 12.4K listening...                         |
    | +---------------------------------------------------+ |
    | | [Request to Speak]               [Mute / Leave]   | |
    | +---------------------------------------------------+ |
    +-------------------------------------------------------+
    ```
*   **Technical Implementation:**
    *   **Core Protocol:** WebRTC via an open-source media server framework like **LiveKit** or a managed provider like **Agora**.
    *   **Role Management:** Host (creator who starts the space), Speakers (invited to speak by Host), and Listeners (default audience).

---

### 2.4. Feature 4: Virtual Stadium Map (Spatial Social Match Stands)
To give fans a visual sense of place, the match page will host an interactive, simplified vector map of a cricket stadium.

*   **UI/UX Layout:**
    *   **The Map Widget:** A clean 2D bird's-eye view of a stadium, sliced into different "Stands" (e.g., *Grand Stand* for tacticians, *Sightscreen Stands* for bowling purists, and *Midwicket Stands* for raw, noisy fan banter).
    *   **Interaction:** Clicking a stand on the map instantly transitions the user's live chat feed to that localized sub-stand, preventing global chat room overload.
    
    **UI Mockup Sketch:**
    ```text
    +-------------------------------------------------------+
    |                    [ STADIUM MAP ]                    |
    |                     /-- Sightscreen --\               |
    |                   /                     \             |
    |                  |  [X] Pitch (Live)     |  Grand Stand|
    |                  |                       |  (Analytical|
    |                   \                     /             |
    |                     \--- Midwicket ---/               |
    |                  [ MI Fan Base (6.4K in Stand) ]      |
    +-------------------------------------------------------+
    ```
*   **Technical Implementation:**
    *   **WebSocket Channel Mapping:** Dynamically route clients to discrete Redis Pub/Sub channels (e.g., `match:id:stand_sightscreen`, `match:id:stand_midwicket`).
    *   **SVG Rendering:** Render stadium maps using lightweight inline SVG paths on the frontend, mapping mouse/tap coordinate polygons directly to stand IDs.

---

### 2.5. Feature 5: Live Fantasy League Battle Widget
Bridges the gap between fantasy sports and real-time social discussion by letting users showcase their fantasy team matchups.

*   **UX Interface:**
    *   Allows users to link their fantasy accounts (e.g., Dream11, Mobile Premier League).
    *   **Live Points Overlay:** A collapsible sidebar widget display tracking real-time fantasy score updates based on live match actions.
    *   **Banter Cards:** Quick-action buttons to generate and share "Brag Cards" or "Cry Cards" directly into the stand chat when their fantasy captain hits a boundary or gets dismissed.
*   **Technical Architecture:**
    *   **Integrations:** Connects to fantasy provider webhook streams or polls unified sports score provider feeds.
    *   **Calculations Engine:** Runs a microservice to update user fantasy tallies ball-by-ball, caching team points in Redis sorted sets to feed the live leaderboards.

---

### 2.6. Feature 6: DRS Crowd-Sourced Verdict Overlay
A real-time, high-engagement micro-voting overlay triggered when a decision is referred to the Third Umpire.

*   **UI/UX Layout:**
    *   **Trigger:** When a DRS review occurs, a full-width card slides in from the bottom of the viewport.
    *   **Voting Interaction:** Fans have 20 seconds to vote "OUT" or "NOT OUT".
    *   **Live Comparison:** Once the clock hits zero, the graph displays the crowd's verdict, which is then compared directly with the official decision in real-time.
    
    **UI Mockup Sketch:**
    ```text
    +-------------------------------------------------------+
    | [🔍 DRS REFERRAL] - OVER 15.4: LBW appeal on Rohit    |
    | "What is your verdict?"                               |
    |  [🔴 OUT (42%)]             [🟢 NOT OUT (58%)]         |
    |                                                       |
    | Time Remaining: 09 seconds                            |
    | Results will lock once Third Umpire starts review.    |
    +-------------------------------------------------------+
    ```
*   **Technical Implementation:**
    *   **Event Hooks:** Listens to API match webhooks for `status: "DRS_REVIEW"`.
    *   **High-Concurrence Handlers:** Leverage Redis In-Memory counters to aggregate 10,000+ votes per second, pushing the finalized state to the clients via WebSockets when the timer expires.

---

### 2.7. Feature 7: Dynamic WebGL Ball-Tracker Replay (3D Visual Replays)
Since live broadcast video rights are extremely expensive, DugOut will bypass licensing issues by rendering real-time 3D simulation replays of critical balls.

*   **UI/UX Layout:**
    *   **The Replay Window:** An expandable 3D canvas showing the pitch, wickets, and ball trajectory.
    *   **Interactive Controls:** Fans can drag to rotate the camera, zoom in, and play back the delivery in slow motion.
    
    **UI Mockup Sketch:**
    ```text
    +-------------------------------------------------------+
    |                 [ WebGL 3D BALL REPLAY ]              |
    |                /--- (Bowler Release) ---\             |
    |               /   *  (In-Air Path)       \            |
    |              |       *                    |           |
    |              |        \__ (Bounce Point)  |           |
    |               \          *                /           |
    |                 \--- * (Hit Wickets!) ---/            |
    |  [<< Play]   [|| Pause]   [Speed: 0.5x]   [Angle: Side]  |
    +-------------------------------------------------------+
    ```
*   **Technical Implementation:**
    *   **Data Source:** Webhooks streaming ball trajectory coordinates (x, y, z arrays of ball locations, velocity, seam deviation).
    *   **Rendering:** Powered by **Three.js / WebGL** using pre-compiled, lightweight assets of stadiums and player skeletons to minimize load times.

---

### 2.8. Feature 8: The AI-Refereed Fan Debate Arena
Settle heated fan arguments through moderated 1-on-1 debate showdowns in front of the match audience.

*   **UX Interface:**
    *   **Challenge System:** A fan can challenge an opposing fan to a "Debate Duel" over a specific event.
    *   **Live Debate Arena:** Once accepted, both users get 3 rounds (120 seconds each) to post their arguments in a special split-screen container.
    *   **AI Referee:** An automated referee verifies facts, detects logical fallacies, and declares a factual score. The audience votes for the "Banter Winner."
    
    **UI Mockup Sketch:**
    ```text
    +-------------------------------------------------------+
    | ⚔️ DEBATE DUEL: "Who is the better T20 captain?"      |
    +-------------------------------------------------------+
    | [CSK_King]: Dhoni got 5   | [MI_Champ]: Rohit got 5   |
    | trophies and did it with  | trophies in fewer seasons |
    | a weaker bowling attack.  | and has a higher win rate.|
    +-------------------------------------------------------+
    | 🤖 AI Ref Verdict: CSK_King's bowling stat is correct.|
    | Community Vote:  [CSK Stand (62%)]  [MI Stand (38%)]  |
    +-------------------------------------------------------+
    ```
*   **Technical Architecture:**
    *   **Moderator Engine:** Executes a background LLM agent (Gemini 2.5 Flash) tasked with evaluating debate inputs for logical structure and fact-checking against the stats database.

---

## 3. AI-Driven Automation System (Internship Spotlight)

As an AI Automation Intern, implementing smart workflows can create massive value. Below are five production-ready AI integration systems designed for DugOut.

### 3.1. System A: AI Live Companion Bot ("Duggy")
An embedded LLM assistant that answers user queries and initiates stats-focused discussions.

**UI Mockup Sketch:**
```text
+-------------------------------------------------------+
| [🤖 Duggy - Live Stats Companion]                    |
+-------------------------------------------------------+
| User: "What is Kohli's strike rate vs Bumrah?"        |
|                                                       |
| Duggy Bot:                                            |
| "In all T20 matches:                                  |
|  - Balls Faced: 92                                    |
|  - Runs Scored: 124                                   |
|  - Strike Rate: 134.8                                 |
|  - Dismissals: 4 times                                |
|                                                       |
| Quick Actions:                                        |
| [ Compare Batting Stats ]   [ Ask about today's pitch ]|
+-------------------------------------------------------+
```

```
User: "What is Virat Kohli's average against spin in the powerplay?"
       |
       v
[Duggy Orchestrator] ---> [SQL/Stats API Retriever] ---> [Fast Database Lookup]
       |                                                           |
       v                                                           v
[Context Injector] (Injects raw stats + conversation history) <----+
       |
       v
[LLM (Gemini 2.5 Flash)] ---> [Structured Markdown Answer with Emotes]
```

*   **Target Pipeline:**
    *   **Query Parser:** Parses the user's intent. If stats-related, it queries the internal sports database first to prevent hallucination.
    *   **LLM Context window:** Injects current match scorecard state, the specific query, and historical stats retrieved.
    *   **Sample Output:**
        > *"Virat Kohli averages **42.3** against off-spin during the powerplay in T20s, striking at **128.5**. In tonight's match, he has faced 6 balls from off-spinners, scoring 8 runs. Watch out for the next over!"*

---

### 3.2. System B: Real-Time Sentiment Engine & Fan Noise Meter
A visual representation of the emotional state of both fanbases throughout a match.

*   **The Architecture:**
    1.  **Chat Ingestion:** Match-stand chat messages are pushed to an asynchronous queue (e.g., BullMQ or Celery).
    2.  **Inference Pipeline:** A lightweight BERT or DistilRoBERTa model fine-tuned on sports sentiment classifies messages in real-time (`[Excitement, Anxiety, Disappointment, Anger, Neutral]`).
    3.  **Time-Series Aggregation:** The scores are aggregated every 10 seconds and stored in a time-series database (e.g., TimescaleDB).
    4.  **UI Visualization:** A real-time line chart ("The Fan Pulse") is displayed above the chat, overlaying the score line to show exactly how wickets or boundaries shifted the emotional balance of the fans.
    
    **UI Mockup Sketch:**
    ```text
    +-------------------------------------------------------+
    |  LIVE FAN PULSE CHART (SENTIMENT RATIO OVER TIME)      |
    |                                                       |
    |  Excitement (CSK)  [======\                        ]  |
    |  Excitement (MI)   [       \________/============  ]  |
    |                                                       |
    |  100% |                                               |
    |       |    /\   (Wicket)                              |
    |   CSK | __/  \          /\                            |
    |   50% |       \________/  \___ (CSK Wins!)            |
    |   MI  |        \  (6s)    /   \__________             |
    |    0% |_________\________/________________________    |
    |       0'        5'      10'       15'       20'       |
    +-------------------------------------------------------+
    ```

```
       [Live Chat Messages]
                |
                v
        [BullMQ Queue]
                |
                v
  [DistilRoBERTa Inference] ---> In-memory classification
                |
                v
      [TimescaleDB Write]  ---> Aggr. every 10s
                |
                v
     [Frontend D3.js Chart] ---> Real-time Sentiment Pulse
```

---

### 3.3. System C: Persona-Based Commentary Generator
Provide alternative audio/text commentary channels generated in real-time by AI personas.

*   **Implementation Strategy:**
    *   System consumes JSON data payloads from live-score webhooks.
    *   A prompt template is selected based on the user's active persona selection.
*   **Persona Configurations:**
    *   **The Gully Critic (Casual/Banter):** Injects regional cricket slang, emojis, and humorous references to dropped catches or slow batting.
    *   **The Data Analyst (Deep Stats):** Focuses on win probabilities, historical match-ups, and expected run rates.
    *   **The Retro Commentator (Nostalgic):** Writes in the style of classic, highly formal radio broadcasts from the 1980s.
*   **Example Prompt Template (The Gully Critic):**
    ```
    System Prompt:
    You are 'Gully Critic', a witty, cricket-obsessed commentator who speaks in a mix of English and local cricket street-slang (e.g., Hinglish/Gully cricket terms like 'Lappa', 'Dot ball pressure'). 
    Commentate on the following ball event. Keep it under 2 sentences, funny, and highly engaging for social media.
    
    Match Data Payload:
    {
      "batsman": "R. Sharma", "bowler": "M. Starc",
      "over": "14.2", "runs": 0, "event": "Play and miss",
      "speed": "148.5 km/h"
    }
    
    Response:
    "Starc throws a fire bolt at 148 clicks and Rohit swings like a wild man but hits pure air! The dot ball pressure is building up big time. Bat pe ball laao, skipper!"
    ```

---

### 3.4. System D: Automated Content & Meme Synthesizer
Auto-generate viral-ready infographics and memes during live matches.

*   **How it Works:**
    1.  **Trigger:** An event qualifies as "Meme-worthy" (e.g., a batsman getting out on a golden duck, a fielder making an spectacular drop, or a bowler taking a hat-trick).
    2.  **AI Image Compositor:** A background job takes pre-existing player cards, overlays the event description, and applies a meme filter.
    3.  **Draft Creation:** The post is auto-saved as a draft for community moderators. Upon approval, it is pushed to the "Trending" feed with auto-generated hashtags, encouraging users to share and comment.

---

### 3.5. System E: Dynamic Auto-Moderator (Anti-Toxicity & Abuse Prevention)
Maintains community health without slowing down real-time chat.

*   **System Design:**
    *   **Tier 1 (Regex & Keyword Blocking):** Instant blocking of blacklisted terms at the client/gateway level (0ms latency).
    *   **Tier 2 (AI Toxicity Filter):** Submits messages asynchronously to a fine-tuned multilingual model (or Google Perspective API) to flag nuanced abuse, racism, and target toxicity.
    *   **Tier 3 (User Rating / Karma):** Users who consistently receive high-toxicity ratings are automatically shadow-banned or put into "read-only" mode during peak matches.

---

### 3.6. System F: Smart Highlight Clipper & AI Thread Generator
Automates content curation during live games to keep the main feed populated with high-quality discussion threads.

*   **Workflow:**
    1.  **Event Detection:** The live scoreboard feed triggers on key events (e.g., a spectacular run-out or a 100-meter six).
    2.  **Buzz Monitor:** A pipeline checks the volume and velocity of chat messages. If a spike is detected, it registers the event as a "Viral Moment."
    3.  **AI Copywriter:** Calls Gemini 2.5 Flash with the event details and recent fan quotes to generate a curated discussion thread header, draft post description, and context tags.
    4.  **Auto-Queue:** Saves the generated post as a draft in the admin portal. Once approved by a moderator, it is pushed to the trending feed.

---

### 3.7. System G: AI Historical Matchup Simulator
Allows fans to settle debate arguments by running simulated matchups between players from different eras (e.g., *1998 Sachin Tendulkar vs. 2024 Jasprit Bumrah*).

*   **Orchestration Flow:**
    1.  **Input:** User requests a matchup through the companion bot (e.g., `Simulate: prime Dhoni batting vs prime Shane Warne`).
    2.  **Stats Retrieval:** Aggregates career statistics, strike rates, bowling variants, and matchup profiles from the sports database.
    3.  **Simulation Engine:** Runs a Monte Carlo over simulation (12 balls) to calculate probabilistic outcomes of each delivery.
    4.  **LLM Commentary:** Feeds the raw simulation logs to Gemini 2.5 Flash to generate a dramatic, ball-by-ball radio-style commentary script, complete with crowd reactions and player emotes.

---

### 3.8. System H: AI Match Sentiment Heatmap Timeline
Provides a visual heatmap seeking bar that maps the "excitement peaks" of the entire match based on social velocity.

*   **Workflow:**
    1.  **Sentiment Mapping:** Consumes logs from the Real-Time Sentiment Engine (System B) and counts chat message frequencies.
    2.  **Peak Classification:** Annotates the timeline bar with colored segments representing high emotional intensity (e.g., Red for wickets, Green for boundaries, Orange for near-misses).
    3.  **Time-Travel Navigation:** Fans can click on any color peak on the timeline to "time-travel" the chat container, loading the historic comments and posts that occurred during that exact over.
    
    **UI Mockup Sketch:**
    ```text
    +-------------------------------------------------------+
    |                 [ MATCH HEATMAP TIMELINE ]            |
    |  Overs: 01      05      10      15      20      Final |
    |  Feeds: [__▒_]  [___█]  [__░_]  [___▓]  [████]  [████]|
    |           ^       ^               ^       ^       ^   |
    |          Open   (Wkt)           (6s)   (Death)  (Win) |
    |  *Clicked Over 15 (▓): Loading historic chat logs...* |
    +-------------------------------------------------------+
    ```
*   **Technical Implementation:**
    *   **Data Aggregation:** Aggregates chat volume and sentiment coefficients per over, storing the structured metadata in Elasticsearch/PostgreSQL.
    *   **Scroll-Anchor API:** Queries chat archives using timestamp indices, dynamically replacing the live feed with historical scroll views.

---

### 3.9. System I: Contextual Social Push Notification Engine
Generates dynamic, real-time push alerts that prioritize social banter over flat score updates.

*   **Workflow:**
    1.  **Trigger Event:** A key event occurs (e.g., Kohli dismissed on a duck).
    2.  **Context Generator:** Checks the user's followed teams and current onboarding profiles.
    3.  **AI Copywriter:** Calls Gemini 2.5 Flash to write a highly targeted, slightly cheeky notification.
        *   *For MI Fans:* *"Your captain just dismissed Kohli! Jump in the MI Stand to cheer the boys!"*
        *   *For RCB Fans:* *"Heartbreak! Kohli departs early. The RCB Stand needs your support right now."*
    4.  **Delivery:** Pushes the notification via Firebase Cloud Messaging (FCM) within 5 seconds of the wicket.
*   **Technical Implementation:**
    *   **User Segment Routing:** Filters active device tokens based on onboarding database tables (`user_favorite_teams`).
    *   **FCM Batching:** Runs an async queue worker to batch delivery and avoid API throttling during high-traffic moments.

---

## 4. Gamification, Predictions & Economy

To build long-term retention loops, we propose a virtual economy inside DugOut:

```
+-------------------------------------------------------------+
|                     DUGOUT COINS SYSTEM                     |
|                                                             |
|   [ Earn Coins ]                                            |
|     |-- Daily check-in (+10 coins)                          |
|     |-- Successful predictions (+variable coins)            |
|     |-- High-quality posts (+5 coins per like)              |
|                                                             |
|   [ Spend Coins ]                                           |
|     |-- Unlock team-specific chat badges (e.g., "Golden Cap")|
|     |-- Access premium expert prediction threads            |
|     |-- Cast votes in major community polls                  |
+-------------------------------------------------------------+
```

### 4.1. Real-Time In-Play Prediction Polls
*   **Mechanism:** Every 2 overs, a system-generated prediction card appears:
    *   *Question:* "Will Virat Kohli score 15+ runs in the next 10 balls?"
    *   *Options:* Yes (1.8x payout) / No (2.1x payout).
*   **Retention Loop:** The quick feedback loop (results are resolved in minutes) keeps fans glued to the screen throughout the match.
    
    **UI Mockup Sketch:**
    ```text
    +-------------------------------------------------------+
    | 🪙 LIVE IN-PLAY PREDICTION (Earn 50 Coins!)            |
    |                                                       |
    | "Will Hardik Pandya hit a Six in the next over?"      |
    |                                                       |
    | [  Option A: YES  ] -> Payout: 1.8x Coins             |
    | [  Option B: NO   ] -> Payout: 2.2x Coins             |
    |                                                       |
    | Time Remaining: 45 seconds                            |
    | Current Voters: 8,421 fans                            |
    +-------------------------------------------------------+
    ```

---

### 4.2. The "Fan Fuel" Team Cheer Meter
An interactive tapping game designed to keep users engaged during live overs.

*   **Mechanism:**
    *   During active balls, a "Cheer" button appears on the screen matching the user's team preference.
    *   **Tapping Interaction:** Users tap the button repeatedly to send visual floaty emojis (team flags, cricket balls) up the side of the chat window, contributing to a live **Team Excitement Score** chart.
    *   **Fuel Resource:** Tapping drains a small "Fan Fuel" gauge. Fuel slowly regenerates automatically or can be refilled using earned **DugOut Coins**.
*   **Value:** Creates a sense of collective action and tribal support during critical game moments, feeding into the timeseries sentiment engine.

---

## 5. UI/UX Design System Extensions

To ensure all new features blend cleanly into the current DugOut visual identity (relying on the design tokens found at `/design-system`), we must strictly adhere to the following layout and design patterns:

### 5.1. The Sticky Live-Score Strip
*   **Desktop Layout:** Mounted as a left-hand navigation sidebar next to the main feed, utilizing the dark base color `#060808` with borders using `#111916` to structure layout lines.
*   **Mobile Layout:** An anchored, collapsible 60px header. When expanded, it slides down to reveal partnership charts and recent ball updates.

### 5.2. Core Color and Typography Integration
We must map all interactive UI components to the established design system tokens:
*   **Primary Backgrounds:** Use `bg.base` (`#060808`) for main screens, `bg.primary` (`#0B0F0D`) for container grids, and `bg.card` (`#151D19`) for chat message rows or prediction boxes.
*   **Cricket Accent Colors:** 
    *   **Live Badges:** Use `accent.red` (`#EF4444`) with pulsing animations to indicate active status.
    *   **Success Actions (Follow/Yes):** Use `green.bright` (`#22C55E`) or `green.primary` (`#1B5E3B`) for action buttons.
    *   **Trend Flags:** Use `accent.orange` (`#FF6B35`) for trending metrics.
*   **Typography Hierarchy:**
    *   **Live Scores:** Always render using `JetBrains Mono` (Bold) to display scores (e.g., `187/4`) and strike rates.
    *   **General Copy:** Render using `Inter` with body text at `14px` (`leading-relaxed`) in `#F3F4F6` for readability.

---

## 6. Architecture & Scalability Challenges

During high-profile tournaments (such as the IPL or ICC World Cup), DugOut must be built to scale up to **100,000+ concurrent connections**.

| Risk | Impact | Mitigation Strategy |
| :--- | :--- | :--- |
| **WebSocket Server Overload** | Crash on high traffic spikes (e.g. final over) | Implement horizontal scaling of Node.js WebSocket instances behind an Nginx load balancer, utilizing Redis Adapter for cross-server message synchronization. |
| **Database Write Bottleneck** | Chat latency increases, rendering feeds stale | Decouple chat writes. Write chat messages to an in-memory queue first (Redis), then write them to Postgres asynchronously in batches of 200. |
| **LLM API Rate Limits** | "Duggy" Bot fails to respond during peak hours | Implement aggressive caching of stats lookup queries (cache TTL: 5 minutes for general stats, 10 seconds for live match stats) to minimize API calls. |
| **API Costs (LLM + Stats API)** | High operational expenses | Use **Gemini 2.5 Flash** for high-velocity, low-cost text operations. Reserve premium models only for complex, daily match-summary generation. |

---

## 7. Strategic Execution Plan (Phased Roadmap)

We propose a phased, agile roadmap to deliver this system incrementally.

### Phase 1: Community Core & Live Stands (Weeks 1 - 4)
*   **Goal:** Build the infrastructure to link conversations directly to scorecards.
*   **Deliverables:**
    1.  WebSocket-based live chat channels tied to match IDs and team stands.
    2.  Sticky mini-scorecard component on mobile and desktop viewports.
    3.  Integration of basic live-score API hooks.
    4.  Interactive SVG-based Stadium Map Widget mapping clicks to stands.
    5.  DRS Crowd-Sourced Verdict Overlay slide-in widget.

### Phase 2: Gamification, Economy & AI Moderation (Weeks 5 - 8)
*   **Goal:** Enhance engagement loops, introduce predictions, and protect community health.
*   **Deliverables:**
    1.  DugOut Coins ledger and live dynamic prediction polls.
    2.  AI-based auto-moderation pipeline (multilingual perspective API / classification models).
    3.  Live Fantasy League Battle Widget overlay with player sharing.
    4.  "Fan Fuel" Cheer Meter tapping widget with visual emoji bursts.
    5.  AI-Refereed Fan Debate Arena challenge system.

### Phase 3: The Intelligent & Audio Platform (Weeks 9 - 12)
*   **Goal:** Fully integrate generative AI systems and launch audio communication.
*   **Deliverables:**
    1.  "Duggy" Bot live stats lookup integration in match chats.
    2.  Fan sentiment timeseries timeline graph on match feeds.
    3.  LiveKit-based Audio Dugouts with speaker role controls.
    4.  AI Historical Matchup Simulator with Monte Carlo simulations and narrative commentary.
    5.  AI Smart Highlight Clipper & automated social thread drafts generator.
    6.  AI Match Sentiment Heatmap Timeline with scroll-anchor time-travel features.
    7.  WebGL 3D Ball-Tracker Replay canvas viewer.
    8.  Contextual Social Push Notification engine (FCM-based).
