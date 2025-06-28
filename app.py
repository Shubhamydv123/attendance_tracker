from flask import Flask, render_template, request, redirect, url_for
import sqlite3
from datetime import datetime

app = Flask(__name__)

def init_db():
    conn = sqlite3.connect('attendance.db')
    c = conn.cursor()
    
    # Students table: name + enrollment_number (unique)
    c.execute('''
        CREATE TABLE IF NOT EXISTS students (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            enrollment TEXT UNIQUE NOT NULL
        )
    ''')
    
    # Subjects table
    c.execute('''
        CREATE TABLE IF NOT EXISTS subjects (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL UNIQUE
        )
    ''')
    
    # Attendance table
    c.execute('''
        CREATE TABLE IF NOT EXISTS attendance (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            student_id INTEGER,
            subject TEXT,
            date TEXT,
            status TEXT,
            FOREIGN KEY(student_id) REFERENCES students(id)
        )
    ''')

    # Default subjects insert
    c.execute("SELECT COUNT(*) FROM subjects")
    if c.fetchone()[0] == 0:
        default_subjects = ['Math', 'AI', 'DSA', 'Python']
        c.executemany("INSERT INTO subjects (name) VALUES (?)", [(sub,) for sub in default_subjects])
    conn.commit()
    conn.close()

@app.route('/')
def index():
    conn = sqlite3.connect('attendance.db')
    c = conn.cursor()
    c.execute("SELECT * FROM students ORDER BY name")
    students = c.fetchall()

    c.execute("SELECT name FROM subjects ORDER BY name")
    subjects = [row[0] for row in c.fetchall()]

    conn.close()
    return render_template('index.html', students=students, subjects=subjects)

# Add student with enrollment
@app.route('/add_student', methods=['POST'])
def add_student():
    name = request.form['name'].strip()
    enrollment = request.form['enrollment'].strip()
    conn = sqlite3.connect('attendance.db')
    c = conn.cursor()
    try:
        c.execute("INSERT INTO students (name, enrollment) VALUES (?, ?)", (name, enrollment))
        conn.commit()
    except sqlite3.IntegrityError:
        # Enrollment must be unique; ignore duplicates silently or handle as you want
        pass
    conn.close()
    return redirect('/')

# Remove student
@app.route('/delete_student/<int:student_id>')
def delete_student(student_id):
    conn = sqlite3.connect('attendance.db')
    c = conn.cursor()
    # Delete attendance first
    c.execute("DELETE FROM attendance WHERE student_id = ?", (student_id,))
    # Delete student
    c.execute("DELETE FROM students WHERE id = ?", (student_id,))
    conn.commit()
    conn.close()
    return redirect('/')

# Edit student (name and enrollment)
@app.route('/edit_student/<int:student_id>', methods=['GET', 'POST'])
def edit_student(student_id):
    conn = sqlite3.connect('attendance.db')
    c = conn.cursor()
    if request.method == 'POST':
        new_name = request.form['name'].strip()
        new_enroll = request.form['enrollment'].strip()
        try:
            c.execute("UPDATE students SET name = ?, enrollment = ? WHERE id = ?", (new_name, new_enroll, student_id))
            conn.commit()
        except sqlite3.IntegrityError:
            # Enrollment number already exists
            pass
        conn.close()
        return redirect('/')
    else:
        c.execute("SELECT name, enrollment FROM students WHERE id = ?", (student_id,))
        student = c.fetchone()
        conn.close()
        if student:
            return render_template('edit_student.html', student_id=student_id, name=student[0], enrollment=student[1])
        else:
            return redirect('/')

@app.route('/mark_attendance', methods=['POST'])
def mark_attendance():
    date = datetime.today().strftime('%Y-%m-%d')
    subject = request.form['subject']
    attendance_data = request.form
    conn = sqlite3.connect('attendance.db')
    c = conn.cursor()
    for student_id, status in attendance_data.items():
        if student_id not in ['submit', 'subject']:
            c.execute("INSERT INTO attendance (student_id, subject, date, status) VALUES (?, ?, ?, ?)", 
                      (student_id, subject, date, status))
    conn.commit()
    conn.close()
    return redirect('/report')

# Subject Management
@app.route('/subjects')
def subjects():
    conn = sqlite3.connect('attendance.db')
    c = conn.cursor()
    c.execute("SELECT * FROM subjects ORDER BY name")
    subjects = c.fetchall()
    conn.close()
    return render_template('subjects.html', subjects=subjects)

@app.route('/add_subject', methods=['POST'])
def add_subject():
    name = request.form['name'].strip()
    conn = sqlite3.connect('attendance.db')
    c = conn.cursor()
    try:
        c.execute("INSERT INTO subjects (name) VALUES (?)", (name,))
        conn.commit()
    except sqlite3.IntegrityError:
        pass
    conn.close()
    return redirect('/subjects')

@app.route('/delete_subject/<int:subject_id>')
def delete_subject(subject_id):
    conn = sqlite3.connect('attendance.db')
    c = conn.cursor()
    c.execute("SELECT name FROM subjects WHERE id = ?", (subject_id,))
    subject_name = c.fetchone()
    if subject_name:
        subject_name = subject_name[0]
        c.execute("DELETE FROM attendance WHERE subject = ?", (subject_name,))
        c.execute("DELETE FROM subjects WHERE id = ?", (subject_id,))
        conn.commit()
    conn.close()
    return redirect('/subjects')

@app.route('/edit_subject/<int:subject_id>', methods=['GET', 'POST'])
def edit_subject(subject_id):
    conn = sqlite3.connect('attendance.db')
    c = conn.cursor()
    if request.method == 'POST':
        new_name = request.form['name'].strip()
        c.execute("SELECT name FROM subjects WHERE id = ?", (subject_id,))
        old_name = c.fetchone()[0]
        try:
            c.execute("UPDATE subjects SET name = ? WHERE id = ?", (new_name, subject_id))
            c.execute("UPDATE attendance SET subject = ? WHERE subject = ?", (new_name, old_name))
            conn.commit()
        except sqlite3.IntegrityError:
            pass
        conn.close()
        return redirect('/subjects')
    else:
        c.execute("SELECT name FROM subjects WHERE id = ?", (subject_id,))
        subject = c.fetchone()
        conn.close()
        if subject:
            return render_template('edit_subject.html', subject_id=subject_id, subject_name=subject[0])
        else:
            return redirect('/subjects')

# Attendance report overall
@app.route('/report')
def report():
    conn = sqlite3.connect('attendance.db')
    c = conn.cursor()
    c.execute('''
        SELECT s.name, s.enrollment, a.subject,
               COUNT(CASE WHEN a.status='Present' THEN 1 END) as present,
               COUNT(*) as total
        FROM attendance a
        JOIN students s ON s.id = a.student_id
        GROUP BY a.subject, a.student_id
        ORDER BY a.subject, s.name
    ''')
    rows = c.fetchall()
    conn.close()

    attendance_data = {}
    for name, enrollment, subject, present, total in rows:
        if subject not in attendance_data:
            attendance_data[subject] = []
        attendance_data[subject].append({
            'name': name,
            'enrollment': enrollment,
            'present': present,
            'total': total,
            'percentage': round((present / total) * 100, 2) if total > 0 else 0
        })

    return render_template('attendance.html', attendance_data=attendance_data)

# Student search form + show attendance summary
@app.route('/student_search', methods=['GET', 'POST'])
def student_search():
    if request.method == 'POST':
        enrollment = request.form['enrollment'].strip()
        conn = sqlite3.connect('attendance.db')
        c = conn.cursor()
        # Get student by enrollment
        c.execute("SELECT id, name FROM students WHERE enrollment = ?", (enrollment,))
        student = c.fetchone()
        if not student:
            conn.close()
            return render_template('student_search.html', error="Student not found", attendance=None, enrollment=enrollment)

        student_id, name = student
        # Get attendance grouped by subject for this student
        c.execute('''
            SELECT subject,
                COUNT(CASE WHEN status='Present' THEN 1 END) as present,
                COUNT(*) as total
            FROM attendance
            WHERE student_id = ?
            GROUP BY subject
        ''', (student_id,))
        attendance_rows = c.fetchall()

        # Calculate overall attendance percentage
        total_present = sum(r[1] for r in attendance_rows)
        total_classes = sum(r[2] for r in attendance_rows)
        overall_percentage = round((total_present / total_classes) * 100, 2) if total_classes > 0 else 0

        conn.close()

        return render_template('student_search.html', attendance=attendance_rows, name=name,
                               enrollment=enrollment, overall=overall_percentage, error=None)
    else:
        return render_template('student_search.html', attendance=None, error=None)

if __name__ == '__main__':
    init_db()
    app.run(debug=True)
