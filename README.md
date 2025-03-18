# AI Interview Agent - Mock Interview API Documentation

This API allows you to simulate an interview process with a candidate using GPT-4o. It generates professional questions, handles candidate responses, and evaluates the interview.

---

## 🚀 How to Run

### 1. **Create a Virtual Environment**

```bash
python -m venv venv
```

### 2. **Activate the Virtual Environment**

* **Windows:**

```bash
.\venv\Scripts\activate
```

* **MacOS/Linux:**

```bash
source venv/bin/activate
```

### 3. **Install Requirements**

```bash
pip install -r requirements.txt
```

### 4. **Create `.env` File**

Create a `.env` file in the root directory and add your OpenAI API key:

```plaintext
OPENAI_API_KEY=sk-proj-...
```

### 5. **Run the App**

```bash
python app.py
```

### ✅ **Python Version**

This project runs on **Python 3.12.7**

---

## 📌 API Endpoints

### 1. **`/start`**

Starts a new interview session and returns the first question.

* **Request:**

  `GET /start`
* **Response:**

```json
{
  "question": "Hello, and thank you for taking the time to speak with me today. To get us started, could you please tell me a little bit about yourself and your professional background? This will help us set the stage for our conversation and allow me to tailor my questions to your unique experiences and expertise."
}
```

---

### 2. **`/respond`**

Processes the candidate’s response and continues the interview.

* **Request:**

  `POST /respond`
* **Request Body:**

```json
{
  "response": "Thank you for having me. I have a background in computer science, and my interest in this field started when I was young, experimenting with coding and building small projects. Over time, I became passionate about solving complex problems and creating innovative solutions, which naturally led me to pursue a career in software development and AI."
}
```

* **Response:**

```json
{
  "message": "That's wonderful to hear about your journey into the field. As we begin our conversation, could you elaborate on any specific projects or experiences during your early years in computer science that were particularly influential in shaping your career path?"
}
```

* **If the interview is completed:**

```json
{
  "message": "Interview completed. Thank you for participating!",
  "status": "completed"
}
```

---

### 3. **`/evaluation`**

Returns the evaluation of the interview once it’s completed.

* **Request:**

  `GET /evaluation`
* **Response:**

```json
{
  "evaluation": "**Introduction:**\nThe candidate introduces themselves with clarity and confidence, focusing on a significant achievement in their role. They effectively highlight the transition from a monolithic architecture to microservices, demonstrating an ability to communicate technical processes and outcomes succinctly.\n- **Score: 8/10**\n\n**Resume Overview:**\nThe candidate provides a relevant and comprehensive overview of their professional background, effectively connecting their past experiences to the successful implementation of complex systems. They articulate their skills in cloud platforms, containerization, and their leadership in transitioning to microservices.\n- **Score: 9/10**\n\n**Technical Evaluation:**\nThe candidate showcases a deep understanding of technical concepts such as event-driven architecture, service mesh implementation, and infrastructure-as-code. Their responses indicate strong problem-solving skills and the ability to implement scalable and maintainable solutions.\n- **Score: 9/10**\n\n**Behavioral Assessment:**\nThe candidate demonstrates strong communication skills, effective conflict resolution, and adaptability in leadership. They provide examples of managing team dynamics and fostering collaboration, indicating their ability to lead and work well in team settings.\n- **Score: 8/10**\n\n**Cultural Fit:**\nThe candidate aligns their personal values with those of the company, emphasizing collaboration, innovation, and inclusivity. They provide examples of initiatives like tech talks and team-building activities, which support a positive team environment and a culture of continuous learning.\n- **Score: 9/10**\n\n**Overall Summary:**\nThe candidate exhibits strong technical expertise and leadership abilities, with a clear alignment to company values. Their ability to articulate past experiences and solve complex problems makes them a strong candidate for roles involving system transformations and team leadership.\n- **Overall Score: 43/50**"
}
```

---

### 4. **`/context`**

Retrieves the current interview context, including exchanged messages between the candidate and interviewer. *(Hidden from UI in Version 1)*

* **Request:**

  `GET /context`
* **Response:**

```json
[
  {
    "candidate": "Certainly. In one role, our company … 30%."
  },
  {
    "interviewer": "Can you elaborate on it?"
  },
  {
    "candidate": "One of the biggest … over 40%."
  }
]
```
