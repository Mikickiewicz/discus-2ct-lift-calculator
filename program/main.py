import sys
from gui import init_gui

def main():
    app, window = init_gui()
    print("Discus-2cT Lift Calculator started")
    sys.exit(app.exec())

if __name__ == "__main__":
    main()
