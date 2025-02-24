# tree_widget.py
import os
import sys
from PyQt5.QtWidgets import QTreeWidget, QMessageBox
from PyQt5.QtCore import pyqtSignal

class MyTreeWidget(QTreeWidget):
    """
    드래그 앤 드롭, 더블 클릭, 노드 검색 기능을 포함한 QTreeWidget 하위 클래스
    """
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAcceptDrops(True)
        self.setDragEnabled(True)

    def mouseDoubleClickEvent(self, event):
        """더블 클릭 시 기본 노드 확장/축소 기능을 막고 사용자 정의 이벤트만 실행"""
        item = self.itemAt(event.pos())
        if item:
            main_window = self.window()
            if hasattr(main_window, "on_tree_item_double_clicked"):
                main_window.on_tree_item_double_clicked(item, 0)
        event.ignore()  # 기본 동작(노드 확장/축소) 방지

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
            main_window = self.window()
            not_found_files = []  # 찾지 못한 파일 리스트

            for url in event.mimeData().urls():
                file_name_no_ext = os.path.splitext(
                    os.path.basename(url.toLocalFile())
                )[0]
                parts = file_name_no_ext.split("_")
                part_number = parts[3] if len(parts) >= 4 else file_name_no_ext
                item = self.find_item(part_number)

                if item:
                    self.setCurrentItem(item)
                    item.setExpanded(True)
                    if hasattr(main_window, "on_tree_item_clicked"):
                        main_window.on_tree_item_clicked(item, 0)
                else:
                    not_found_files.append(file_name_no_ext)  # 찾지 못한 파일 저장

            # 찾지 못한 파일이 있을 경우 경고 메시지 표시
            if not_found_files:
                QMessageBox.warning(
                    self, "파일 노드 없음",
                    f"다음 파일과 일치하는 노드를 찾을 수 없습니다:\n\n" + "\n".join(not_found_files),
                    QMessageBox.Ok
                )

            event.acceptProposedAction()
        else:
            event.ignore()

    def find_item(self, text):
        """
        재귀적으로 트리 내에서 주어진 텍스트와 일치하는 노드를 검색
        """
        def recursive_search(item):
            if item.text(0) == text:
                return item
            for i in range(item.childCount()):
                found = recursive_search(item.child(i))
                if found:
                    return found
            return None

        for i in range(self.topLevelItemCount()):
            found = recursive_search(self.topLevelItem(i))
            if found:
                return found
        return None
