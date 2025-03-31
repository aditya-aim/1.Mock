import requests

url = "http://localhost:5022/start"

file_path = r"C:\Users\AnalyticsIndiaMag\Desktop\aditya\PROJECTS\JOB-TOOLKIT\1.Mock\templates\Aditya.pdf"

data = {
    "company_name": "AIM Media",
    "job_role": "AI ML Engineer",
    "job_description": "Detailed job description...",
    "difficulty": "medium",
}

with open(file_path, "rb") as file:
    files = {"resume": ("resume.pdf", file, "application/pdf")}
    response = requests.post(url, files=files, data=data)

print("Status Code:", response.status_code)
print("Response Text:", response.text)
