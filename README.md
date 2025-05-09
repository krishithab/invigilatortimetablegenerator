# Invigilation Timetable System

A web-based system for automatically scheduling exam invigilators based on their availability and exam requirements.

## Setup Instructions

1. Create a virtual environment (recommended):
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Run the application:
```bash
python app.py
```

4. Open your browser and navigate to: `http://localhost:5000`

## File Format Requirements

### Exam Schedule (CSV)
```csv
day,date,subject,form,start_time,duration
Monday,01-Jan,Mathematics,5A,09:00,2
Tuesday,02-Jan,Science,5B,11:00,1.5
```

### Invigilator Schedule (CSV)
```csv
initial,max_hours,monday,tuesday,wednesday,thursday,friday
TCH1,10,09:00-12:00,10:00-12:00,09:00-11:00,,
TCH2,8,,09:00-11:00,13:00-15:00,10:00-12:00,09:00-11:00
```

## Features

- Upload exam and invigilator schedules in CSV format
- Automatic allocation of invigilators based on availability
- Download complete schedule in Excel format
- View assignment statistics and summary
- Sample files provided for reference

## Notes

- Times should be in 24-hour format (HH:MM)
- Duration is in hours (can be decimal, e.g., 1.5 for 1 hour 30 minutes)
- Weekly schedule should use time ranges (e.g., 09:00-12:00) 
