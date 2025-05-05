from flask import Flask, render_template, request, redirect, url_for, flash, send_file
import os
from datetime import datetime, time, timedelta
import pandas as pd
import io
import math
import zipfile
from typing import List, Dict, Optional, Tuple

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = os.path.join(os.getcwd(), 'uploads')
app.secret_key = os.environ.get('SECRET_KEY', 'dev-key-please-change')  # More secure secret key handling

# Create uploads folder if it doesn't exist
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

class Invigilator:
    def __init__(self, initial: str, max_hours: float, weekly_schedule: Dict[str, str] = None):
        self.initial = initial
        self.max_hours = max_hours
        self.assigned_hours = 0.0
        self.weekly_schedule = weekly_schedule if weekly_schedule else {
            'monday': '', 'tuesday': '', 'wednesday': '', 'thursday': '', 'friday': ''
        }
        self.invigilations = []  # List of assigned exams

    def is_available(self, exam_day: str, exam_start: str, exam_end: str) -> bool:
        """Check if invigilator is available for exam"""
        exam_day = exam_day.lower()
        exam_start = self._str_to_time(exam_start)
        exam_end = self._str_to_time(exam_end)
        
        # Check weekly schedule availability
        if not self._is_within_weekly_schedule(exam_day, exam_start, exam_end):
            return False
            
        # Check existing invigilations for conflicts
        for invigilation in self.invigilations:
            if invigilation['day'].lower() == exam_day and self._time_overlap(
                (exam_start, exam_end),
                (invigilation['start_time'], invigilation['end_time'])
            ):
                return False
                
        # Check total hours availability
        exam_duration = (exam_end.hour - exam_start.hour) + (exam_end.minute - exam_start.minute)/60
        return (self.max_hours - self.assigned_hours) >= exam_duration

    def _is_within_weekly_schedule(self, day: str, start: time, end: time) -> bool:
        """Check if time falls within regular weekly schedule"""
        available_slots = self.weekly_schedule.get(day, '').split(',')
        for slot in available_slots:
            if not slot.strip():
                continue
            try:
                slot_start, slot_end = [self._str_to_time(t.strip()) for t in slot.split('-')]
                if (start >= slot_start and end <= slot_end):
                    return True
            except (ValueError, AttributeError):
                continue
        return False

    @staticmethod
    def _str_to_time(time_str: str) -> time:
        """Convert 'HH:MM' string to time object"""
        if isinstance(time_str, str):
            return datetime.strptime(time_str, '%H:%M').time()
        return time_str  # Already a time object

    @staticmethod
    def _time_overlap(range1: Tuple[time, time], range2: Tuple[time, time]) -> bool:
        """Check if two time ranges overlap"""
        start1, end1 = range1
        start2, end2 = range2
        return max(start1, start2) < min(end1, end2)

    def assign_exam(self, exam_data: Dict) -> None:
        """Assign an exam to this invigilator"""
        start = self._str_to_time(exam_data['start_time'])
        end = self._str_to_time(exam_data['end_time'])
        duration = (end.hour - start.hour) + (end.minute - start.minute)/60
        
        self.invigilations.append(exam_data)
        self.assigned_hours += duration

class Exam:
    def __init__(self, day: str, date: str, subject: str, form: str, 
                 start_time: str, duration: float, invigilators_needed: int = 2):
        self.day = day
        self.date = date
        self.subject = subject
        self.form = form
        self.start_time = start_time  # 'HH:MM'
        self.duration = duration  # in hours
        self.invigilators_needed = invigilators_needed
        self.invigilators = []  # List of Invigilator objects
        
    @property
    def end_time(self) -> str:
        """Calculate end time as 'HH:MM' string"""
        start = datetime.strptime(self.start_time, '%H:%M')
        end = start + timedelta(hours=self.duration)
        return end.strftime('%H:%M')
        
    def to_dict(self) -> Dict:
        """Convert exam to dictionary for processing"""
        return {
            'day': self.day,
            'date': self.date,
            'subject': self.subject,
            'form': self.form,
            'start_time': self.start_time,
            'end_time': self.end_time,
            'duration': self.duration,
            'required': self.invigilators_needed,
            'assigned': len(self.invigilators),
            'invigilators': ', '.join([inv.initial for inv in self.invigilators])
        }

def allocate_invigilators(exams: List[Exam], invigilators: List[Invigilator]) -> bool:
    """Assign invigilators to exams using greedy algorithm"""
    # Sort exams by duration (longest first)
    exams.sort(key=lambda x: x.duration, reverse=True)
    
    for exam in exams:
        available = [inv for inv in invigilators if inv.is_available(
            exam.day, exam.start_time, exam.end_time
        )]
        
        # Sort by remaining availability (least remaining hours first)
        available.sort(key=lambda x: x.max_hours - x.assigned_hours)
        
        # Assign required invigilators
        needed = min(exam.invigilators_needed, len(available))
        for i in range(needed):
            inv = available[i]
            exam.invigilators.append(inv)
            inv.assign_exam({
                'day': exam.day,
                'date': exam.date,
                'subject': exam.subject,
                'start_time': exam.start_time,
                'end_time': exam.end_time,
                'duration': exam.duration
            })
    
    return True

def process_files(exam_path: str, invigilator_path: str) -> Optional[Dict]:
    """Process uploaded CSV files and return results"""
    try:
        # Load data
        exams_df = pd.read_csv(exam_path)
        invig_df = pd.read_csv(invigilator_path)
        
        # Create invigilator objects
        invigilators = []
        for _, row in invig_df.iterrows():
            weekly_schedule = {
                'monday': str(row.get('monday', '')),
                'tuesday': str(row.get('tuesday', '')),
                'wednesday': str(row.get('wednesday', '')),
                'thursday': str(row.get('thursday', '')),
                'friday': str(row.get('friday', ''))
            }
            invigilators.append(Invigilator(
                initial=str(row['initial']),
                max_hours=float(row['max_hours']),
                weekly_schedule=weekly_schedule
            ))
        
        # Create exam objects
        exams = []
        for _, row in exams_df.iterrows():
            exams.append(Exam(
                day=str(row['day']),
                date=str(row['date']),
                subject=str(row['subject']),
                form=str(row['form']),
                start_time=str(row['start_time']),
                duration=float(row['duration'])
            ))
        
        # Allocate invigilators
        success = allocate_invigilators(exams, invigilators)
        
        # Prepare results
        exam_results = [exam.to_dict() for exam in exams]
        total_exams = len(exams)
        total_required = sum(exam.invigilators_needed for exam in exams)
        total_assigned = sum(len(exam.invigilators) for exam in exams)
        assignment_rate = math.floor((total_assigned/total_required)*100) if total_required > 0 else 0
        
        # Prepare invigilator summary
        invigilator_summary = []
        for inv in invigilators:
            invigilator_summary.append({
                'initial': inv.initial,
                'total_hours': inv.max_hours,
                'assigned_hours': round(inv.assigned_hours, 1),
                'remaining_hours': round(inv.max_hours - inv.assigned_hours, 1),
                'assigned_exams': len(inv.invigilations),
                'weekly_schedule': format_schedule(inv.weekly_schedule)
            })
        
        return {
            'results': exam_results,
            'total_exams': total_exams,
            'total_required': total_required,
            'total_assigned': total_assigned,
            'assignment_rate': assignment_rate,
            'invigilator_summary': invigilator_summary
        }
        
    except Exception as e:
        flash(f'Error processing files: {str(e)}', 'error')
        return None

def format_schedule(schedule: Dict) -> str:
    """Format weekly schedule for display"""
    parts = []
    for day in ['monday', 'tuesday', 'wednesday', 'thursday', 'friday']:
        if schedule.get(day, '').strip():
            parts.append(f"{day[:3]}: {schedule[day]}")
    return ' | '.join(parts) if parts else 'Not specified'

@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        # Check files
        if 'exam_file' not in request.files or 'invigilator_file' not in request.files:
            flash('Both files are required', 'error')
            return redirect(request.url)
            
        exam_file = request.files['exam_file']
        invigilator_file = request.files['invigilator_file']
        
        if exam_file.filename == '' or invigilator_file.filename == '':
            flash('No selected files', 'error')
            return redirect(request.url)
            
        # Save files
        os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
        exam_path = os.path.join(app.config['UPLOAD_FOLDER'], 'exams.csv')
        invig_path = os.path.join(app.config['UPLOAD_FOLDER'], 'invigilators.csv')
        
        try:
            exam_file.save(exam_path)
            invigilator_file.save(invig_path)
        except Exception as e:
            flash(f'Error saving files: {str(e)}', 'error')
            return redirect(request.url)
        
        # Process files
        result = process_files(exam_path, invig_path)
        if result is None:
            return redirect(request.url)
            
        return render_template('index.html', **result)
    
    return render_template('index.html')

@app.route('/download')
def download():
    try:
        exam_path = os.path.join(app.config['UPLOAD_FOLDER'], 'exams.csv')
        invig_path = os.path.join(app.config['UPLOAD_FOLDER'], 'invigilators.csv')
        
        result = process_files(exam_path, invig_path)
        if not result:
            flash('No data available to download', 'error')
            return redirect(url_for('index'))
        
        # Create Excel file
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
            # Exam schedule
            exam_df = pd.DataFrame(result['results'])
            exam_df['status'] = exam_df.apply(
                lambda x: 'Complete' if x['assigned'] >= x['required'] else 'Incomplete', 
                axis=1
            )
            exam_df.to_excel(writer, sheet_name='Exam Schedule', index=False)
            
            # Invigilator summary
            invig_df = pd.DataFrame(result['invigilator_summary'])
            invig_df.to_excel(writer, sheet_name='Invigilators', index=False)
            
            # Summary stats
            stats_df = pd.DataFrame({
                'Total Exams': [result['total_exams']],
                'Required Invigilators': [result['total_required']],
                'Assigned Invigilators': [result['total_assigned']],
                'Assignment Rate': [f"{result['assignment_rate']}%"]
            })
            stats_df.to_excel(writer, sheet_name='Summary', index=False)
            
        output.seek(0)
        
        return send_file(
            output,
            mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
            download_name='invigilation_schedule.xlsx',
            as_attachment=True
        )
        
    except Exception as e:
        flash(f'Error generating download: {str(e)}', 'error')
        return redirect(url_for('index'))

@app.route('/sample_files')
def sample_files():
    # Sample exam data
    exam_data = """day,date,subject,form,start_time,duration
Monday,01-Jan,Mathematics,5A,09:00,2
Tuesday,02-Jan,Science,5B,11:00,1.5
Wednesday,03-Jan,English,5C,14:00,1"""
    
    # Sample invigilator data
    invig_data = """initial,max_hours,monday,tuesday,wednesday,thursday,friday
TCH1,10,09:00-12:00,10:00-12:00,09:00-11:00,,
TCH2,8,,09:00-11:00,13:00-15:00,10:00-12:00,09:00-11:00
TCH3,12,10:00-15:00,,,,13:00-16:00"""
    
    # Create zip file
    zip_buffer = io.BytesIO()
    with zipfile.ZipFile(zip_buffer, 'w') as zip_file:
        zip_file.writestr('exam_sample.csv', exam_data)
        zip_file.writestr('invigilator_sample.csv', invig_data)
    zip_buffer.seek(0)
    
    return send_file(
        zip_buffer,
        mimetype='application/zip',
        as_attachment=True,
        download_name='invigilation_samples.zip'
    )

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)