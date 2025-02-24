import os
import sys
from PyQt5.QtWidgets import QApplication
from ui import MainWindow
from tree_manager import get_base_path, build_tree_view

def main():
    app = QApplication(sys.argv)
    window = MainWindow()

    base_path = get_base_path()
    excelfolder_path = os.path.join(base_path, "01_excel")
    excel_file_path = os.path.join(excelfolder_path, "data.xlsx")
    
    # JSON 파일 경로를 01_excel 폴더 내부로 지정
    json_file_path = os.path.join(excelfolder_path, "memo.json")
    # 폴더가 없으면 생성
    if not os.path.exists(excelfolder_path):
        os.makedirs(excelfolder_path)
    
    window.json_file_path = json_file_path
    window.load_memo_data()
    
    if os.path.exists(excel_file_path):
        build_tree_view(excel_file_path, window)
    
    window.show()
    sys.exit(app.exec_())

if __name__ == "__main__":
    main()
