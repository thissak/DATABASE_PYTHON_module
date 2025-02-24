# ui.py
from PyQt5.QtWidgets import (
    QMainWindow, QTreeWidget, QTextEdit, QVBoxLayout, QHBoxLayout,
    QWidget, QLabel, QRadioButton, QGroupBox, QPushButton, QSpacerItem, QSizePolicy, QCheckBox,
    )
from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtGui import QFont, QFontMetrics
from tree_widget import MyTreeWidget

# 클릭 가능한 QLabel
class ClickableLabel(QLabel):
    clicked = pyqtSignal()
    
    def mousePressEvent(self, event):
        self.clicked.emit()
        super().mousePressEvent(event)

# UI 구성만 담당하는 클래스
class MainWindowUI:
    def setupUi(self, MainWindow):
        MainWindow.setObjectName("MainWindow")
        MainWindow.resize(1000, 1600)
        
        # ─── 좌측: 트리뷰 + 로그창 ──────────────────────────────
        self.tree = MyTreeWidget(self)
        self.tree.setColumnCount(1)
        self.tree.setHeaderLabels(["FA-50M FINAL ASSEMBLY VERSION POLAND"])
        
        self.logText = QTextEdit(MainWindow)
        self.logText.setReadOnly(True)
        self.logText.setFixedHeight(300)
        
        leftLayout = QVBoxLayout()
        leftLayout.addWidget(self.tree, 3)
        leftLayout.addWidget(self.logText, 1)
        leftLayout.setSpacing(25)
        leftWidget = QWidget()
        leftWidget.setLayout(leftLayout)
        
        # ─── 우측 상단: 이미지 패널 ──────────────────────────────
        self.imageLabel = ClickableLabel("이미지가 여기에 표시됩니다.", MainWindow)
        self.imageLabel.setAlignment(Qt.AlignHCenter | Qt.AlignCenter)
        self.imageLabel.setStyleSheet("border: 1px solid gray;")
        self.imageLabel.setFixedSize(400, 400)
        
        # ─── 공통 스타일 ───────────────────────────────────────
        self.qgroupbox_style = (
            "QGroupBox { background-color: #f0f0f0; border: 1px solid gray; margin-top: 10px; }"
            "QGroupBox::title { subcontrol-origin: margin; subcontrol-position: top center; padding: 0 3px; font-weight: bold; }"
        )
        self.button_style = (
            "QPushButton { background-color: lightgray; border: 2px solid gray; border-radius: 5px; padding: 8px; font-size: 20px; }"
            "QPushButton:checked, QPushButton:pressed { background-color: yellow; border: 2px solid orange; }"
        )
        
        # ─── 라디오 버튼 그룹 + Filter 버튼 ───────────────────
        self.radio_image = QRadioButton("Image", MainWindow)
        self.radio_3dxml = QRadioButton("3DXML", MainWindow)
        self.radio_fbx = QRadioButton("FBX", MainWindow)
        self.radio_image.setChecked(True)

        self.filter_button = QPushButton("Filter", MainWindow)
        self.filter_button.setCheckable(True)
        self.filter_button.setMinimumSize(130, 40)
        self.filter_button.setStyleSheet(self.button_style)

        # 라디오 버튼 가로 레이아웃
        radio_layout = QHBoxLayout()
        radio_layout.addWidget(self.radio_image)
        radio_layout.addWidget(self.radio_3dxml)
        radio_layout.addWidget(self.radio_fbx)
        radio_layout.setSpacing(35)
        radio_layout.setAlignment(Qt.AlignCenter)

        # FILE 체크박스 생성 (예: "Show in Explorer" 이름 사용)
        self.checkbox_file = QCheckBox("Show in Explorer", MainWindow)
        self.checkbox_file.setChecked(False)

        # 현재 폰트를 복사해서 bold 폰트로 변경한 후, 텍스트 너비를 측정하여 고정 너비 설정
        font = self.checkbox_file.font()
        bold_font = QFont(font)
        bold_font.setBold(True)
        fm = QFontMetrics(bold_font)
        self.checkbox_file.setFixedWidth(fm.horizontalAdvance(self.checkbox_file.text()) + 30)

        # toggled 시 체크 여부에 따라 폰트 굵기를 변경
        self.checkbox_file.toggled.connect(
            lambda checked: self.checkbox_file.setStyleSheet("font-weight: bold;" if checked else "font-weight: normal;")
        )

        # Filter 버튼과 FILE 체크박스를 같은 행에 배치
        filter_layout = QHBoxLayout()
        filter_layout.addStretch()
        filter_layout.addWidget(self.filter_button)
        filter_layout.addSpacing(10)
        filter_layout.addWidget(self.checkbox_file)
        filter_layout.addStretch()

        # 상단 라디오 버튼과 하단 Filter+FILE 레이아웃을 수직으로 배치
        radio_main_layout = QVBoxLayout()
        radio_main_layout.addLayout(radio_layout)
        radio_main_layout.addLayout(filter_layout)

        self.radio_group = QGroupBox("Select mode", MainWindow)
        self.radio_group.setStyleSheet(self.qgroupbox_style)
        self.radio_group.setFixedHeight(180)
        self.radio_group.setLayout(radio_main_layout)

        
        # ─── 메모 그룹 ─────────────────────────────────────────
        self.memo_group = QGroupBox("Memo", MainWindow)
        self.memo_group.setStyleSheet(self.qgroupbox_style)
        memo_layout = QVBoxLayout()
        
        # 읽기 전용 메모 출력 박스
        self.memoOutput = QTextEdit(MainWindow)
        self.memoOutput.setReadOnly(True)
        self.memoOutput.setFixedHeight(150)
        self.memoOutput.setStyleSheet("QTextEdit { background-color: #e0e0e0; }")
        
        # 메모 입력 박스 (사용자 입력용)
        self.memoText = QTextEdit(MainWindow)
        self.memoText.setFixedHeight(150)
        self.memoText.setStyleSheet("QTextEdit { text-align: left; }")
        
        # 버튼 레이아웃 (Save Memo, Clear Memo)
        button_layout = QHBoxLayout()
        self.memoSaveButton = QPushButton("Save Memo", MainWindow)
        self.memoSaveButton.setStyleSheet(self.button_style)

        self.memoClearButton = QPushButton("Clear Memo", MainWindow)
        self.memoClearButton.setStyleSheet(self.button_style)
        button_layout.addWidget(self.memoSaveButton)
        button_layout.addWidget(self.memoClearButton)
        
        memo_layout.addWidget(self.memoOutput)
        memo_layout.addWidget(self.memoText)
        memo_layout.addLayout(button_layout)
        self.memo_group.setLayout(memo_layout)
        self.memo_group.setFixedHeight(480)
        
        # ─── 우측 전체 레이아웃 ─────────────────────────────
        rightLayout = QVBoxLayout()
        rightLayout.addWidget(self.imageLabel)
        rightLayout.addWidget(self.radio_group)
        rightLayout.addWidget(self.memo_group)
        rightLayout.setSpacing(25)  # 우측 그룹 간 간격

        # ─── 보이지 않는 SpacerItem 추가 (하단 공간 차지 → 위젯을 위로 올림)
        spacer = QSpacerItem(20, 20, QSizePolicy.Minimum, QSizePolicy.Expanding)
        rightLayout.addItem(spacer)
        
        rightWidget = QWidget()
        rightWidget.setLayout(rightLayout)
        
        # ─── 메인 레이아웃 ─────────────────────────────
        mainLayout = QHBoxLayout()
        mainLayout.addWidget(leftWidget, 4)
        mainLayout.addWidget(rightWidget, 3)
        centralWidget = QWidget()
        centralWidget.setLayout(mainLayout)
        MainWindow.setCentralWidget(centralWidget)
