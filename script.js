document.addEventListener('DOMContentLoaded', function() {
    // Handle file input changes
    document.getElementById('exam_file').addEventListener('change', function() {
        document.getElementById('exam-file-name').textContent = this.files[0].name;
    });

    document.getElementById('invigilator_file').addEventListener('change', function() {
        document.getElementById('invigilator-file-name').textContent = this.files[0].name;
    });

    // Form validation
    document.getElementById('uploadForm').addEventListener('submit', function(e) {
        const examFile = document.getElementById('exam_file').files[0];
        const invigilatorFile = document.getElementById('invigilator_file').files[0];

        if (!examFile || !invigilatorFile) {
            e.preventDefault();
            alert('Please select both exam and invigilator files.');
        }
    });

    // Auto-dismiss alerts after 5 seconds
    const alerts = document.querySelectorAll('.alert');
    alerts.forEach(alert => {
        setTimeout(() => {
            alert.classList.remove('show');
            setTimeout(() => alert.remove(), 150);
        }, 5000);
    });
}); 