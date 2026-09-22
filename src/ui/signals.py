from PyQt6.QtCore import QObject, pyqtSignal

class ProgressSignal(QObject):
    progress = pyqtSignal(str, str, float)
    finished = pyqtSignal()
    canceled = pyqtSignal()
    error = pyqtSignal(str)
    
    hide_window = pyqtSignal()
    show_window = pyqtSignal()
    
    versions_loaded = pyqtSignal(list)
    update_available = pyqtSignal(str, str)