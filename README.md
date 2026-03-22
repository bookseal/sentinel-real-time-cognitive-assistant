# 🎙️ Real-time Cognitive Assistant (RTCA)

> **"Bridging the gap between human conversation and machine-verified intelligence."**

## 1. Project Purpose
The **Real-time Cognitive Assistant (RTCA)** is a high-performance system designed to act as an external "Prefrontal Cortex" during complex meetings. Built with **OpenAI's Realtime API** and **LangGraph**, it aims to:
* **Augment Emotional Intelligence**: Provide real-time visual alerts for high-stress situations].
* **Enhance Decision Accuracy**: Detect information with low credibility and trigger instant fact-checks].
* **Scale Intellectual Leverage**: Convert raw meeting audio into structured, actionable insights for the "Individual Contributor"].

---

## 2. Decision Matrix: Architectural Strategy

This system follows the **Well-Architected Framework** to ensure operational excellence and scalability].

| Strategy | **High Analytical Depth (Batch)** | **Ultra-Low Latency (Streaming)** |
| :--- | :--- | :--- |
| **High Complexity** | Post-meeting deep-dive reports | **[Target] Real-time Cognitive Intervention** |
| **Low Complexity** | Basic speech-to-text archiving | Real-time captions / Subtitles |

---

## 3. Core Feature: The "Red Light" (Emotional Intensity Monitor)

The assistant continuously monitors the meeting's emotional climate. When vocal arousal exceeds the defined threshold, a **Red Light** status is triggered to alert the user of potential "emotional hijacking."

### 🧠 The Mathematical Logic
The Emotional Intensity Index ($E$) is calculated as follows:

$$E = \omega_1 \cdot \Delta P + \omega_2 \cdot V_{rms} + \omega_3 \cdot S_{agg}$$

- **$\Delta P$ (Pitch Variance)**: Measures the fluctuation in vocal frequency, indicating stress or excitement.
- **$V_{rms}$ (Volume Root-Mean-Square)**: Tracks energy levels; sudden spikes often correlate with shouting or interruptions.
- **$S_{agg}$ (Aggressive Sentiment)**: Semantic analysis of word choices (e.g., confrontational vs. collaborative).
- **Intuitive Meaning**: "The system ignores normal excitement but triggers an alert when the combination of voice-shaking, loud volume, and sharp language suggests a loss of objectivity."

---

## 4. Evolutionary Roadmap
1.  **Stage 1 (MVP)**: Persistent background listening with "Red Light" visual trigger for high-arousal emotions.
2.  **Stage 2 (Agentic Fact-Check)**: Integration of **LangGraph** to identify factual claims and verify them via search agents (e.g., Tavily)].
3.  **Stage 3 (Cloud-Native Deployment)**: Migrating the backend to **k3s on Oracle Cloud (OCI)** with **Traefik** for secure, low-latency streaming].

---

## 5. TODO List: Phase 1 (Emotion Red Light Implementation)

To meet the standards of a **Global AI Platform Engineer**, we focus on modularity and resilience].

### 🛠️ Infrastructure & Connectivity
* [ ] **API Orchestration**: Implement WebSocket client for `gpt-realtime-1.5`].
* [ ] **Gradio Interface**: Create a dashboard with a dynamic HTML status indicator (Green/Yellow/Red).
* [ ] **Environment Security**: Securely manage API keys using `.env` (Zero-trust approach)].

### 🎙️ Audio Engineering
* [ ] **Chunked Streaming**: Implement `gr.Audio(streaming=True)` with 500ms intervals.
* [ ] **VAD (Voice Activity Detection)**: Integrate **Silero VAD** locally to reduce API costs and noise].

### 🤖 Logic & Sentiment Analysis
* [ ] **System Prompting**: Design a system message that instructs the agent to return a JSON object with `emotion_score` and `justification`].
* [ ] **Asynchronous Processing**: Use Python `asyncio` to prevent UI blocking during API calls.
* [ ] **Damping Filter**: Implement a sliding window average (e.g., last 3 seconds) to ensure status light stability.

---

## 🚩 Red Flag & Proactive Alternative
**The Red Flag**: Relying solely on text-based sentiment may cause "False Positives" for enthusiastic but non-aggressive speakers].

**The Alternative**: Use a **Multimodal Weighting System**. Combine the LLM's text sentiment analysis with raw audio metadata (RMS energy). If text is "Aggressive" but volume is "Normal," categorize it as "Sarcasm" rather than a "Red Light" alert].

---
© 2026 Gichan Lee. Built on the foundations of 42 Seoul and Microsoft Technical Excellence].
