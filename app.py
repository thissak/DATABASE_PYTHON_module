import os
import sys
import time
import pandas as pd
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QTreeWidget, QTreeWidgetItem,
    QTextEdit, QVBoxLayout, QHBoxLayout, QWidget, QLabel, QMessageBox
)
from PyQt5.QtGui import QFont, QPixmap
from PyQt5.QtCore import Qt, QUrl
from PyQt5.QtGui import QDesktopServices

# modules.py에 정의된 함수와 전역변수 불러오기
from modules import (
    get_base_path, build_tree_view, image_dict, display_part_info
)

# ─────────────────────────────────────────────────────────────
# MyTreeWidget: 드래그앤드롭 및 노드 검색 기능 제공
# ─────────────────────────────────────────────────────────────
class MyTreeWidget(QTreeWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAcceptDrops(True)
        self.setDragEnabled(True)
    
    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()
        else:
            event.ignore()
    
    def dragMoveEvent(self, event):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()
        else:
            event.ignore()
    
    def dropEvent(self, event):
        if event.mimeData().hasUrls():
            found_nodes = []
            not_found = []
            main_window = self.window()
            for url in event.mimeData().urls():
                file_path = url.toLocalFile()
                file_name = os.path.basename(file_path)
                ext = os.path.splitext(file_name)[1].lower()
                if ext not in [".png", ".jpg"]:
                    QMessageBox.warning(self, "잘못된 파일", "JPG 또는 PNG 파일만 허용됩니다.")
                    continue
                file_name_no_ext = os.path.splitext(file_name)[0]
                parts = file_name_no_ext.split("_")
                if len(parts) >= 4:
                    part_number = parts[3]
                else:
                    part_number = file_name_no_ext
                item = self.find_item(part_number)
                if item:
                    self.setCurrentItem(item)
                    item.setExpanded(True)
                    found_nodes.append(part_number)
                    if hasattr(main_window, "on_tree_item_clicked"):
                        main_window.on_tree_item_clicked(item, 0)
                else:
                    not_found.append(part_number)
            msg = ""
            if found_nodes:
                msg += "찾은 노드:\n" + "\n".join(found_nodes)
            if not_found:
                if msg:
                    msg += "\n\n"
                msg += "찾지 못한 노드:\n" + "\n".join(not_found)
            if msg:
                if hasattr(main_window, "appendLog"):
                    main_window.appendLog(msg)
                else:
                    print(msg)
            event.acceptProposedAction()
        else:
            event.ignore()
    
    def find_item(self, text):
        def recursive_search(item):
            if item.text(0) == text:
                return item
            for i in range(item.childCount()):
                found = recursive_search(item.child(i))
                if found:
                    return found
            return None
        
        for i in range(self.topLevelItemCount()):
            top_item = self.topLevelItem(i)
            found = recursive_search(top_item)
            if found:
                return found
        return None

# ─────────────────────────────────────────────────────────────
# MainWindow: 트리뷰, 로그창, 이미지 패널 포함
# ─────────────────────────────────────────────────────────────
class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Parts Treeview + Drag&Drop + Image Panel")
        self.resize(1000, 1600)
        
        self.df = None  # 엑셀 데이터 저장
        
        self.tree = MyTreeWidget()
        self.tree.setColumnCount(1)
        self.tree.setHeaderLabels(["FA-50M FINAL ASSEMBLY VERSION POLAND"])
        self.tree.itemClicked.connect(self.on_tree_item_clicked)
        self.tree.itemDoubleClicked.connect(self.on_tree_item_double_clicked)
        
        # 로그창 생성
        self.logText = QTextEdit()
        self.logText.setReadOnly(True)
        self.logText.setFixedHeight(300)
        
        # 이미지 패널 생성
        self.imageLabel = QLabel("이미지가 여기에 표시됩니다.", self)
        self.imageLabel.setAlignment(Qt.AlignHCenter | Qt.AlignCenter)
        self.imageLabel.setStyleSheet("border: 1px solid gray;")
        self.imageLabel.setFixedSize(400, 400)
        
        leftLayout = QVBoxLayout()
        leftLayout.addWidget(self.tree, stretch=3)
        leftLayout.addWidget(self.logText, stretch=1)
        leftWidget = QWidget()
        leftWidget.setLayout(leftLayout)
        
        rightLayout = QVBoxLayout()
        rightLayout.addWidget(self.imageLabel)
        rightWidget = QWidget()
        rightWidget.setLayout(rightLayout)
        
        mainLayout = QHBoxLayout()
        mainLayout.addWidget(leftWidget, stretch=4)
        mainLayout.addWidget(rightWidget, stretch=3)
        centralWidget = QWidget()
        centralWidget.setLayout(mainLayout)
        self.setCentralWidget(centralWidget)
    
    def appendLog(self, message):
        self.logText.append(message)
    
    def on_tree_item_clicked(self, item, column):
        part_no = item.text(column)
        if part_no in image_dict:
            image_path = image_dict[part_no]
            if os.path.exists(image_path):
                pixmap = QPixmap(image_path)
                if not pixmap.isNull():
                    scaled = pixmap.scaled(
                        self.imageLabel.width(),
                        self.imageLabel.height(),
                        Qt.KeepAspectRatio,
                        Qt.SmoothTransformation
                    )
                    self.imageLabel.setPixmap(scaled)
                else:
                    self.imageLabel.clear()
                    self.imageLabel.setText("이미지 로드 실패.")
            else:
                self.imageLabel.clear()
                self.imageLabel.setText("이미지가 없습니다.")
        else:
            self.imageLabel.clear()
            self.imageLabel.setText("이미지가 없습니다.")
        display_part_info(part_no, self)
    
    def on_tree_item_double_clicked(self, item, column):
        """
        더블클릭 시 해당 이미지 파일을 기본 이미지 뷰어로 열기
        """
        part_no = item.text(column)
        if part_no in image_dict:
            image_path = image_dict[part_no]
            if os.path.exists(image_path):
                QDesktopServices.openUrl(QUrl.fromLocalFile(image_path))
            else:
                QMessageBox.warning(self, "경고", "이미지 파일이 존재하지 않습니다.")
        else:
            QMessageBox.warning(self, "경고", "해당 파트넘버에 해당하는 이미지가 없습니다.")

def main():
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    
    # 현재 폴더에서 엑셀 파일 로드
    base_path = get_base_path()
    excelfolder_path = os.path.join(base_path, "01_excel")
    excel_file_path = os.path.join(excelfolder_path, "data.xlsx")
    
    if os.path.exists(excel_file_path):
        build_tree_view(excel_file_path, window)
    else:
        QMessageBox.warning(None, "파일 없음", "data.xlsx 파일을 찾을 수 없습니다!")
    
    sys.exit(app.exec_())

if __name__ == "__main__":
    main()
