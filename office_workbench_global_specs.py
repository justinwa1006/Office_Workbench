import sys, json, os, shutil
from pathlib import Path
from datetime import datetime, date
from uuid import uuid4

from PySide6.QtCore import Qt, QDate, QSize, QUrl
from PySide6.QtGui import QColor, QFont, QDesktopServices, QPixmap
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QLineEdit, QComboBox, QDateEdit, QCheckBox, QTableWidget,
    QTableWidgetItem, QHeaderView, QMessageBox, QInputDialog, QFileDialog,
    QDialog, QFormLayout, QDialogButtonBox, QFrame, QTreeWidget,
    QTreeWidgetItem, QSplitter, QToolButton, QTextEdit, QListWidget, QListWidgetItem
)

APP_DIR = Path(__file__).resolve().parent
DATA_ROOT = APP_DIR / "Office Workbench Data"
SETTINGS = DATA_ROOT / "settings.json"

DARK_THEME = '''
QMainWindow,QWidget{background:#0b151e;color:#e8f0f4;font:10pt "Segoe UI","Malgun Gothic"}
QLabel{background:transparent}
QFrame#top,QFrame#card{background:#11212d;border:1px solid #2e4859;border-radius:10px}
QLabel#title{font-size:18pt;font-weight:800;color:#ffffff}
QLabel#stat{font-size:20pt;font-weight:800;color:#55e0d6}
QLabel#hint{color:#9db1bb}
QPushButton{background:#1a2c3a;color:#edf5f7;border:1px solid #405c6e;border-radius:7px;padding:8px 12px;font-weight:700}
QPushButton:hover{background:#274050}
QPushButton#primary{background:#0e9186;border-color:#34d0c4;color:white}
QLineEdit,QComboBox,QDateEdit,QTextEdit,QTableWidget{background:#0c1923;color:#eef5f7;border:1px solid #3a5669;border-radius:7px;padding:7px}
QHeaderView::section{background:#172936;color:#dce8ed;padding:8px;border:none;border-right:1px solid #344e5e}
QTableWidget{gridline-color:#2c4353;selection-background-color:#285167;selection-color:white}
QTreeWidget{background:#10202c;color:#e8f0f4;border:1px solid #2e4859;border-radius:9px;padding:6px}
QTreeWidget::item{background:transparent;padding:7px 8px;border-radius:6px;margin:1px 2px}
QTreeWidget::item:hover{background:#18313e}
QTreeWidget::item:selected{background:#164b56;color:white;border-left:4px solid #55e0d6}
QToolButton#completeBox{background:transparent;border:none;color:#dce8ed;font-size:18pt;font-weight:400;padding:0px}
QToolButton#completeBox:checked{color:#55e0d6}
QCheckBox{background:transparent}
QCheckBox::indicator{width:18px;height:18px}
'''

LIGHT_THEME = '''
QMainWindow,QWidget{background:#f4f7f9;color:#20313c;font:10pt "Segoe UI","Malgun Gothic"}
QLabel{background:transparent}
QFrame#top,QFrame#card{background:#ffffff;border:1px solid #cfdae1;border-radius:10px}
QLabel#title{font-size:18pt;font-weight:800;color:#17303d}
QLabel#stat{font-size:20pt;font-weight:800;color:#087f77}
QLabel#hint{color:#617783}
QPushButton{background:#ffffff;color:#243a46;border:1px solid #b9c9d2;border-radius:7px;padding:8px 12px;font-weight:700}
QPushButton:hover{background:#eaf4f4;border-color:#65aaa5}
QPushButton#primary{background:#087f77;border-color:#087f77;color:#ffffff}
QPushButton#primary:hover{background:#066c66}
QLineEdit,QComboBox,QDateEdit,QTextEdit,QTableWidget{background:#ffffff;color:#20313c;border:1px solid #bdccd5;border-radius:7px;padding:7px}
QHeaderView::section{background:#e8eff3;color:#29414e;padding:8px;border:none;border-right:1px solid #cad6dd}
QTableWidget{gridline-color:#d8e1e6;selection-background-color:#d6efed;selection-color:#17303d}
QTreeWidget{background:#ffffff;color:#20313c;border:1px solid #cfdae1;border-radius:9px;padding:6px}
QTreeWidget::item{background:transparent;padding:7px 8px;border-radius:6px;margin:1px 2px}
QTreeWidget::item:hover{background:#edf6f5}
QTreeWidget::item:selected{background:#d6efed;color:#17303d;border-left:4px solid #169a90}
QToolButton#completeBox{background:transparent;border:none;color:#607985;font-size:18pt;font-weight:400;padding:0px}
QToolButton#completeBox:checked{color:#087f77}
QCheckBox{background:transparent}
QCheckBox::indicator{width:18px;height:18px}
'''



def now():
    return datetime.now().isoformat(timespec='seconds')


def atomic_write(path: Path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    backup = path.with_suffix('.backup.json')
    tmp = path.with_suffix(path.suffix + '.tmp')
    if path.exists():
        try:
            json.loads(path.read_text(encoding='utf-8')); shutil.copy2(path, backup)
        except Exception: pass
    tmp.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding='utf-8')
    json.loads(tmp.read_text(encoding='utf-8'))
    os.replace(tmp, path)


class SortableItem(QTableWidgetItem):
    def __init__(self, text='', sort_key=None):
        super().__init__(str(text)); self.sort_key = sort_key if sort_key is not None else str(text).lower()
    def __lt__(self, other):
        return self.sort_key < other.sort_key if isinstance(other, SortableItem) else super().__lt__(other)


class ProjectStore:
    def __init__(self, folder: Path):
        self.folder = folder
        self.task_file = folder / 'tasks.json'
        self.trash_file = folder / 'trash.json'
        self.meeting_file = folder / 'meetings.json'
        self.spec_file = folder / 'spec_changes.json'
        self.project_file = folder / 'project.json'
        folder.mkdir(parents=True, exist_ok=True)
        if not self.project_file.exists():
            atomic_write(self.project_file, {'name': folder.name, 'created_at': now()})
        self.meta = self._load(self.project_file, {'name': folder.name, 'code': ''})
        self.meta.setdefault('name', folder.name); self.meta.setdefault('code', '')
        self.tasks = self._load(self.task_file, [])
        self.trash = self._load(self.trash_file, [])
        self.meetings = self._load(self.meeting_file, [])
        self.spec_changes = self._load(self.spec_file, [])

    @staticmethod
    def _load(path, default):
        if not path.exists(): return default
        try: return json.loads(path.read_text(encoding='utf-8'))
        except Exception:
            backup=path.with_suffix('.backup.json')
            try:
                recovered=json.loads(backup.read_text(encoding='utf-8')); shutil.copy2(backup,path); return recovered
            except Exception:
                corrupt=path.with_name(path.name+'.corrupt.'+datetime.now().strftime('%Y%m%d_%H%M%S'))
                try: shutil.copy2(path,corrupt)
                except Exception: pass
                return default


    def save(self):
        atomic_write(self.project_file, self.meta)
        atomic_write(self.task_file, self.tasks)
        atomic_write(self.trash_file, self.trash)
        atomic_write(self.meeting_file, self.meetings)
        atomic_write(self.spec_file, self.spec_changes)


class AttachmentWidget(QWidget):
    IMAGE_EXTENSIONS = {'.png','.jpg','.jpeg','.bmp','.gif','.webp'}
    def __init__(self, project_folder, category, attachments=None, parent=None):
        super().__init__(parent)
        self.project_folder=Path(project_folder); self.category=category; self.attachments=list(attachments or [])
        root=QHBoxLayout(self); root.setContentsMargins(0,0,0,0); root.setSpacing(10)
        left=QVBoxLayout(); self.list=QListWidget(); self.list.setMinimumHeight(150); self.list.setMinimumWidth(260)
        self.list.currentItemChanged.connect(self.update_preview); self.list.itemDoubleClicked.connect(self.open_selected); left.addWidget(self.list)
        buttons=QHBoxLayout(); add=QPushButton('+ 캡처본 추가'); open_btn=QPushButton('원본 열기'); remove=QPushButton('제거')
        add.clicked.connect(self.add_files); open_btn.clicked.connect(self.open_selected); remove.clicked.connect(self.remove_selected)
        buttons.addWidget(add); buttons.addWidget(open_btn); buttons.addWidget(remove); buttons.addStretch(); left.addLayout(buttons)
        preview_box=QVBoxLayout(); self.preview=QLabel('캡처본을 선택하면 미리보기가 표시됩니다.'); self.preview.setAlignment(Qt.AlignCenter); self.preview.setMinimumSize(300,190); self.preview.setMaximumHeight(260); self.preview.setStyleSheet('border:1px solid #3a5669;border-radius:7px;padding:6px;background:transparent;')
        self.preview_name=QLabel(''); self.preview_name.setObjectName('hint'); self.preview_name.setAlignment(Qt.AlignCenter); self.preview_name.setWordWrap(True)
        preview_box.addWidget(self.preview,1); preview_box.addWidget(self.preview_name)
        root.addLayout(left,1); root.addLayout(preview_box,1); self.reload()
    def reload(self):
        self.list.clear()
        for rel in self.attachments:
            item=QListWidgetItem(Path(rel).name); item.setData(Qt.UserRole,rel); item.setToolTip(str(self.project_folder/rel)); self.list.addItem(item)
        if self.list.count(): self.list.setCurrentRow(0)
        else: self.clear_preview()
    def clear_preview(self):
        self.preview.setPixmap(QPixmap()); self.preview.setText('캡처본을 선택하면 미리보기가 표시됩니다.'); self.preview_name.setText('')
    def update_preview(self, current, previous=None):
        if not current: self.clear_preview(); return
        path=self.project_folder/current.data(Qt.UserRole); self.preview_name.setText(path.name)
        if not path.exists(): self.preview.setPixmap(QPixmap()); self.preview.setText('파일을 찾을 수 없습니다.'); return
        pixmap=QPixmap(str(path))
        if pixmap.isNull(): self.preview.setPixmap(QPixmap()); self.preview.setText('미리보기를 표시할 수 없습니다.'); return
        size=self.preview.size(); scaled=pixmap.scaled(max(280,size.width()-12),max(170,size.height()-12),Qt.KeepAspectRatio,Qt.SmoothTransformation)
        self.preview.setText(''); self.preview.setPixmap(scaled)
    def resizeEvent(self, event):
        super().resizeEvent(event)
        if self.list.currentItem(): self.update_preview(self.list.currentItem())
    def add_files(self):
        files,_=QFileDialog.getOpenFileNames(self,'캡처본 선택','', '이미지 파일 (*.png *.jpg *.jpeg *.bmp *.gif *.webp)')
        if not files:return
        target_dir=self.project_folder/'attachments'/self.category; target_dir.mkdir(parents=True,exist_ok=True)
        added=[]
        for src_text in files:
            src=Path(src_text)
            if src.suffix.lower() not in self.IMAGE_EXTENSIONS:continue
            target=target_dir/f'{datetime.now().strftime("%Y%m%d_%H%M%S_%f")}_{src.name}'
            shutil.copy2(src,target); rel=str(target.relative_to(self.project_folder))
            if rel not in self.attachments:self.attachments.append(rel); added.append(rel)
        self.reload()
        if added:
            for i in range(self.list.count()):
                if self.list.item(i).data(Qt.UserRole)==added[-1]: self.list.setCurrentRow(i); break
    def selected_path(self):
        item=self.list.currentItem(); return self.project_folder/item.data(Qt.UserRole) if item else None
    def open_selected(self, *_):
        path=self.selected_path()
        if not path: QMessageBox.information(self,'캡처본 선택','열 캡처본을 선택하세요.'); return
        if not path.exists(): QMessageBox.warning(self,'파일 없음','캡처본 파일을 찾을 수 없습니다.'); return
        QDesktopServices.openUrl(QUrl.fromLocalFile(str(path)))
    def remove_selected(self):
        item=self.list.currentItem()
        if not item:return
        rel=item.data(Qt.UserRole)
        if QMessageBox.question(self,'첨부 제거','목록에서 제거할까요? 파일도 함께 삭제됩니다.')!=QMessageBox.Yes:return
        path=self.project_folder/rel
        try:
            if path.exists():path.unlink()
        except Exception as e: QMessageBox.warning(self,'삭제 실패',str(e));return
        self.attachments=[x for x in self.attachments if x!=rel];self.reload()
    def values(self):return list(self.attachments)


class MeetingDialog(QDialog):
    def __init__(self, parent=None, meeting=None, project_folder=None):
        super().__init__(parent); meeting=meeting or {}; self.project_folder=Path(project_folder or APP_DIR); self.setWindowTitle('회의록 수정' if meeting else '새 회의록'); self.setMinimumSize(920,700)
        f=QFormLayout(self); self.title=QLineEdit(meeting.get('title','')); self.meeting_date=QDateEdit(calendarPopup=True); self.meeting_date.setDisplayFormat('yyyy-MM-dd'); self.meeting_date.setDate(QDate.fromString(meeting.get('meeting_date',''),'yyyy-MM-dd') if meeting.get('meeting_date') else QDate.currentDate())
        self.attendees=QLineEdit(meeting.get('attendees','')); self.content=QTextEdit(meeting.get('content','')); self.decisions=QTextEdit(meeting.get('decisions','')); self.actions=QTextEdit(meeting.get('actions',''))
        self.attachments=AttachmentWidget(self.project_folder,'meetings',meeting.get('attachments',[]),self)
        f.addRow('회의 제목',self.title); f.addRow('회의일',self.meeting_date); f.addRow('참석자',self.attendees); f.addRow('회의 내용',self.content); f.addRow('결정사항',self.decisions); f.addRow('후속 조치',self.actions); f.addRow('캡처본',self.attachments)
        b=QDialogButtonBox(QDialogButtonBox.Save|QDialogButtonBox.Cancel); b.button(QDialogButtonBox.Save).setText('저장'); b.button(QDialogButtonBox.Cancel).setText('취소'); b.accepted.connect(self.accept); b.rejected.connect(self.reject); f.addRow(b)
    def values(self):
        return {'title':self.title.text().strip(),'meeting_date':self.meeting_date.date().toString('yyyy-MM-dd'),'attendees':self.attendees.text().strip(),'content':self.content.toPlainText().strip(),'decisions':self.decisions.toPlainText().strip(),'actions':self.actions.toPlainText().strip(),'attachments':self.attachments.values()}


class SpecChangeDialog(QDialog):
    def __init__(self, parent=None, item=None, project_folder=None):
        super().__init__(parent); item=item or {}; self.project_folder=Path(project_folder or APP_DIR); self.setWindowTitle('사양 변경 수정' if item else '사양 변경 등록'); self.setMinimumSize(920,650)
        f=QFormLayout(self); self.change_date=QDateEdit(calendarPopup=True); self.change_date.setDisplayFormat('yyyy-MM-dd'); self.change_date.setDate(QDate.fromString(item.get('change_date',''),'yyyy-MM-dd') if item.get('change_date') else QDate.currentDate())
        self.title=QLineEdit(item.get('title','')); self.before=QTextEdit(item.get('before','')); self.after=QTextEdit(item.get('after',''))
        self.before.setPlaceholderText('변경 전 사양 또는 동작'); self.after.setPlaceholderText('변경 후 사양 또는 동작')
        for w in (self.before,self.after): w.setMaximumHeight(105)
        self.attachments=AttachmentWidget(self.project_folder,'spec_changes',item.get('attachments',[]),self)
        f.addRow('변경일',self.change_date); f.addRow('변경 제목',self.title); f.addRow('변경 전',self.before); f.addRow('변경 후',self.after); f.addRow('캡처본',self.attachments)
        b=QDialogButtonBox(QDialogButtonBox.Save|QDialogButtonBox.Cancel); b.button(QDialogButtonBox.Save).setText('저장'); b.button(QDialogButtonBox.Cancel).setText('취소'); b.accepted.connect(self.accept); b.rejected.connect(self.reject); f.addRow(b)
    def values(self):
        return {'change_date':self.change_date.date().toString('yyyy-MM-dd'),'title':self.title.text().strip(),'before':self.before.toPlainText().strip(),'after':self.after.toPlainText().strip(),'attachments':self.attachments.values()}
    def accept(self):
        if not self.title.text().strip(): QMessageBox.warning(self,'입력 필요','변경 제목을 입력하세요.'); return
        super().accept()


class TaskDialog(QDialog):
    def __init__(self, parent=None, task=None):
        super().__init__(parent); task=task or {}; self.setWindowTitle('업무 수정' if task else '업무 추가'); self.setMinimumWidth(480)
        form=QFormLayout(self); self.title=QLineEdit(task.get('title','')); self.owner=QLineEdit(task.get('owner',''))
        self.start_date=QDateEdit(calendarPopup=True); self.start_date.setDisplayFormat('yyyy-MM-dd'); start=task.get('start_date',(task.get('created_at') or now())[:10]); self.start_date.setDate(QDate.fromString(start,'yyyy-MM-dd') if start else QDate.currentDate())
        self.due=QDateEdit(calendarPopup=True); self.due.setDisplayFormat('yyyy-MM-dd'); self.due.setDate(QDate.currentDate()); self.no_due=QCheckBox('마감일 미정'); due=task.get('due','')
        if due:self.due.setDate(QDate.fromString(due,'yyyy-MM-dd'))
        else:self.no_due.setChecked(True);self.due.setDisabled(True)
        self.no_due.toggled.connect(self.due.setDisabled); due_row=QHBoxLayout();due_row.addWidget(self.due);due_row.addWidget(self.no_due)
        self.priority=QComboBox();self.priority.addItems(['높음','중간','낮음']);self.priority.setCurrentText(task.get('priority','중간'))
        form.addRow('업무 내용',self.title);form.addRow('담당자',self.owner);form.addRow('시작일',self.start_date);form.addRow('마감일',due_row);form.addRow('중요도',self.priority)
        box=QDialogButtonBox(QDialogButtonBox.Save|QDialogButtonBox.Cancel);box.button(QDialogButtonBox.Save).setText('저장');box.button(QDialogButtonBox.Cancel).setText('취소');box.accepted.connect(self.accept);box.rejected.connect(self.reject);form.addRow(box)
    def values(self):
        return {'title':self.title.text().strip(),'owner':self.owner.text().strip(),'start_date':self.start_date.date().toString('yyyy-MM-dd'),'due':'' if self.no_due.isChecked() else self.due.date().toString('yyyy-MM-dd'),'priority':self.priority.currentText()}
    def accept(self):
        if not self.title.text().strip(): QMessageBox.warning(self,'입력 필요','업무 내용을 입력하세요.');return
        if not self.no_due.isChecked() and self.due.date()<self.start_date.date(): QMessageBox.warning(self,'날짜 확인','마감일은 시작일보다 빠를 수 없습니다.\n날짜를 다시 확인해 주세요.');return
        super().accept()


class SimpleWorkbench(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle('Office Workbench')
        self.resize(1180, 760)
        self.setMinimumSize(900, 600)
        DATA_ROOT.mkdir(parents=True, exist_ok=True)
        self.store = None
        self.current_folder = None
        self.filter_text = ''
        self.current_view = '전체 업무'
        self.theme = 'dark'
        self.build_ui()
        self.load_theme()
        self.load_recent_or_empty()

    def build_ui(self):
        root = QWidget(); self.setCentralWidget(root)
        outer = QVBoxLayout(root); outer.setContentsMargins(18,18,18,18); outer.setSpacing(12)

        top = QFrame(); top.setObjectName('top'); top_l = QHBoxLayout(top)
        title = QLabel('Office Workbench'); title.setObjectName('title')
        self.project_label = QLabel('열린 프로젝트 없음'); self.project_label.setObjectName('hint')
        project = QPushButton('프로젝트 관리'); project.clicked.connect(self.project_menu)
        self.theme_btn = QPushButton('☀ 라이트 모드'); self.theme_btn.setToolTip('라이트/다크 모드 전환'); self.theme_btn.clicked.connect(self.toggle_theme)
        self.add_btn = QPushButton('+ 업무 추가'); self.add_btn.setObjectName('primary'); self.add_btn.clicked.connect(self.add_task)
        top_l.addWidget(title); top_l.addSpacing(10); top_l.addWidget(self.project_label); top_l.addStretch(); top_l.addWidget(self.theme_btn); top_l.addWidget(project); top_l.addWidget(self.add_btn)
        outer.addWidget(top)

        splitter = QSplitter(Qt.Horizontal)
        sidebar = QFrame(); sidebar.setObjectName('card'); side = QVBoxLayout(sidebar)
        side_title = QLabel('프로젝트 목록'); side_title.setObjectName('title')
        side_title.setStyleSheet('font-size:13pt;')
        self.project_tree = QTreeWidget(); self.project_tree.setHeaderHidden(True)
        self.project_tree.itemClicked.connect(self.on_tree_click)
        new_btn = QPushButton('+ 새 프로젝트'); new_btn.setObjectName('primary'); new_btn.clicked.connect(self.new_project)
        self.global_specs_btn = QPushButton('사양 변경 모아보기'); self.global_specs_btn.setToolTip('모든 프로젝트의 사양 변경 기록을 한 번에 확인합니다'); self.global_specs_btn.clicked.connect(self.open_global_spec_changes)
        side.addWidget(side_title); side.addWidget(new_btn); side.addWidget(self.global_specs_btn); side.addWidget(self.project_tree,1)
        sidebar.setMinimumWidth(270); sidebar.setMaximumWidth(380)
        splitter.addWidget(sidebar)

        content = QWidget(); main = QVBoxLayout(content); main.setContentsMargins(12,0,0,0); main.setSpacing(12)
        stats = QHBoxLayout()
        self.total = self.stat_card('전체')
        self.active = self.stat_card('진행중')
        self.done = self.stat_card('완료')
        for card, _ in (self.total,self.active,self.done): stats.addWidget(card)
        main.addLayout(stats)

        tools = QHBoxLayout()
        self.view_label = QLabel('전체 업무'); self.view_label.setStyleSheet('font-size:12pt;font-weight:800;color:#55e0d6;background:transparent;')
        self.search = QLineEdit(); self.search.setPlaceholderText('업무 내용 또는 담당자 검색')
        self.search.textChanged.connect(self.refresh)
        self.incomplete = QCheckBox('미완료만')
        self.incomplete.setToolTip('완료되지 않은 업무만 표시합니다')
        self.incomplete.toggled.connect(self.refresh)
        clear = QPushButton('검색 초기화'); clear.clicked.connect(self.search.clear)
        export = QPushButton('Excel 내보내기'); export.clicked.connect(self.export_excel)
        tools.addWidget(self.view_label); tools.addSpacing(8); tools.addWidget(self.search, 1); tools.addWidget(self.incomplete); tools.addWidget(clear); tools.addWidget(export)
        main.addLayout(tools)

        self.table = QTableWidget(0,8)
        self.table.setHorizontalHeaderLabels(['완료','업무 내용','담당자','시작일','마감일','중요도','상태','완료일'])
        self.table.setEditTriggers(QTableWidget.NoEditTriggers); self.table.setSortingEnabled(True); self.table.horizontalHeader().setSortIndicatorShown(True)
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        self.table.setSelectionMode(QTableWidget.SingleSelection)
        self.table.verticalHeader().setVisible(False)
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        self.table.setColumnWidth(1, 460)
        for c in (0,2,3,4,5,6,7): self.table.horizontalHeader().setSectionResizeMode(c, QHeaderView.ResizeToContents)
        self.table.doubleClicked.connect(self.on_task_double_click)
        main.addWidget(self.table, 1)

        bottom = QHBoxLayout()
        edit = QPushButton('선택 수정'); edit.clicked.connect(self.edit_task)
        delete = QPushButton('선택 삭제'); delete.clicked.connect(self.delete_task)
        trash = QPushButton('휴지통 열기'); trash.clicked.connect(self.open_trash)
        source = QPushButton('원본 회의록'); source.setToolTip('회의록에서 생성된 업무의 원본 회의록을 엽니다'); source.clicked.connect(self.open_selected_task_source)
        hint = QLabel('체크박스=완료 · 더블클릭=수정 · 삭제=휴지통'); hint.setObjectName('hint')
        bottom.addWidget(edit); bottom.addWidget(delete); bottom.addWidget(trash); bottom.addWidget(source); bottom.addStretch(); bottom.addWidget(hint)
        main.addLayout(bottom)
        splitter.addWidget(content); splitter.setStretchFactor(1,1)
        outer.addWidget(splitter,1)
        self.reload_project_tree()

    def stat_card(self, label):
        card = QFrame(); card.setObjectName('card'); lay = QVBoxLayout(card)
        num = QLabel('0'); num.setObjectName('stat'); num.setAlignment(Qt.AlignCenter)
        text = QLabel(label); text.setAlignment(Qt.AlignCenter)
        lay.addWidget(num); lay.addWidget(text)
        return card, num

    def reload_project_tree(self):
        if not hasattr(self,'project_tree'): return
        current=str(self.current_folder) if self.current_folder else ''
        self.project_tree.clear(); DATA_ROOT.mkdir(parents=True,exist_ok=True)
        for folder in sorted([p for p in DATA_ROOT.iterdir() if p.is_dir()]):
            meta=ProjectStore._load(folder/'project.json',{'name':folder.name,'code':''}); tasks=ProjectStore._load(folder/'tasks.json',[])
            name=(meta.get('name') or folder.name).strip(); code=(meta.get('code') or '').strip(); total=len(tasks); incomplete=sum(t.get('status')!='완료' for t in tasks); display=f'{code} {name}'.strip() if code else name
            root=QTreeWidgetItem([f'{display}\n업무 {total} · 미완료 {incomplete}']); root.setData(0,Qt.UserRole,str(folder)); root.setExpanded(str(folder)==current); root.setSizeHint(0,QSize(0,54)); font=QFont(); font.setBold(True); root.setFont(0,font)
            for label in ('전체 업무','진행중','완료 업무','회의록','사양 변경','휴지통'):
                child=QTreeWidgetItem([label]); child.setData(0,Qt.UserRole,str(folder)); child.setData(0,Qt.UserRole+1,label); root.addChild(child)
            self.project_tree.addTopLevelItem(root)

    def on_tree_click(self, item, column):
        folder = Path(item.data(0, Qt.UserRole) or '')
        if not folder: return
        if not self.current_folder or folder != self.current_folder:
            self.open_project(folder)
        view = item.data(0, Qt.UserRole + 1) or '전체 업무'
        if view == '회의록': self.open_meetings(); return
        if view == '사양 변경': self.open_spec_changes(); return
        if view == '휴지통':
            self.open_trash(); return
        self.current_view = view
        self.view_label.setText(view)
        self.refresh()

    def load_theme(self):
        try:
            data=json.loads(SETTINGS.read_text(encoding='utf-8')) if SETTINGS.exists() else {}
            self.theme=data.get('theme','dark')
        except Exception: self.theme='dark'
        self.apply_theme()

    def apply_theme(self):
        self.setStyleSheet(LIGHT_THEME if self.theme=='light' else DARK_THEME)
        if hasattr(self,'theme_btn'): self.theme_btn.setText('☾ 다크 모드' if self.theme=='light' else '☀ 라이트 모드')

    def toggle_theme(self):
        self.theme='light' if self.theme=='dark' else 'dark'; self.apply_theme()
        data={}
        try: data=json.loads(SETTINGS.read_text(encoding='utf-8')) if SETTINGS.exists() else {}
        except Exception: pass
        data['theme']=self.theme; atomic_write(SETTINGS,data)

    def load_recent_or_empty(self):
        try:
            if SETTINGS.exists():
                p = Path(json.loads(SETTINGS.read_text(encoding='utf-8')).get('recent',''))
                if (p/'project.json').exists(): self.open_project(p); return
        except Exception: pass
        self.set_project_state(False)

    def set_project_state(self, active):
        self.add_btn.setVisible(active)
        self.search.setEnabled(active)
        self.table.setEnabled(active)
        if not active:
            self.project_label.setText('프로젝트를 먼저 만들어 주세요')
            self.table.setRowCount(0)
            for _, n in (self.total,self.active,self.done): n.setText('0')

    def project_menu(self):
        choices = ['새 프로젝트 만들기','프로젝트 열기','현재 프로젝트 정보 수정','현재 프로젝트 폴더 열기']
        if self.store: choices.append('현재 프로젝트 삭제')
        choice, ok = QInputDialog.getItem(self, '프로젝트', '원하는 작업을 선택하세요.', choices, 0, False)
        if not ok: return
        if choice == choices[0]: self.new_project()
        elif choice == choices[1]: self.pick_project()
        elif choice == choices[2]: self.edit_project_info()
        elif choice == choices[3]:
            if self.current_folder: os.startfile(str(self.current_folder)) if os.name=='nt' else None
        else: self.delete_project()

    def new_project(self):
        code,ok=QInputDialog.getText(self,'새 프로젝트','프로젝트 코드 (선택)')
        if not ok:return
        name,ok=QInputDialog.getText(self,'새 프로젝트','프로젝트명')
        if not ok:return
        code=code.strip(); name=name.strip()
        if not name:
            QMessageBox.warning(self,'입력 필요','프로젝트명을 입력하세요.'); return
        folder=DATA_ROOT/('_'.join(x for x in (code,name) if x).replace('/','_').replace('\\','_'))
        if folder.exists(): QMessageBox.warning(self,'같은 프로젝트','같은 프로젝트가 이미 있습니다.'); return
        folder.mkdir(parents=True); atomic_write(folder/'project.json',{'name':name or code,'code':code,'created_at':now()}); self.open_project(folder)

    def edit_project_info(self):
        if not self.store:return
        code,ok=QInputDialog.getText(self,'프로젝트 정보 수정','프로젝트 코드',text=self.store.meta.get('code',''))
        if not ok:return
        name,ok=QInputDialog.getText(self,'프로젝트 정보 수정','프로젝트명',text=self.store.meta.get('name',self.current_folder.name))
        if not ok or not name.strip():return
        self.store.meta.update({'code':code.strip(),'name':name.strip(),'updated_at':now()}); self.store.save(); self.reload_project_tree(); self.update_project_header()

    def pick_project(self):
        p = QFileDialog.getExistingDirectory(self,'프로젝트 폴더 선택',str(DATA_ROOT))
        if p: self.open_project(Path(p))

    def open_project(self, folder):
        self.current_folder = Path(folder)
        self.store = ProjectStore(self.current_folder)
        for sub in ('전체 업무','진행중','완료 업무','회의록','사양 변경','휴지통'):
            (self.current_folder / sub).mkdir(exist_ok=True)
        atomic_write(SETTINGS, {'recent': str(self.current_folder), 'theme': self.theme})
        self.update_project_header()
        self.set_project_state(True); self.reload_project_tree(); self.refresh()

    def update_project_header(self):
        code=self.store.meta.get('code','').strip(); name=self.store.meta.get('name',self.current_folder.name).strip(); display=f'{code} {name}'.strip()
        self.project_label.setText(f'{display}  ·  자동 저장'); self.setWindowTitle(f'{display} | Office Workbench')

    def delete_project(self):
        if not self.store: return
        name = self.current_folder.name
        typed, ok = QInputDialog.getText(self,'프로젝트 삭제',f'영구 삭제하려면 프로젝트 이름을 입력하세요.\n{name}')
        if not ok or typed != name: return
        if QMessageBox.question(self,'최종 확인','프로젝트와 모든 업무를 삭제합니다. 계속할까요?') != QMessageBox.Yes: return
        shutil.rmtree(self.current_folder)
        self.store = None; self.current_folder = None
        atomic_write(SETTINGS, {'recent': '', 'theme': self.theme}); self.set_project_state(False); self.reload_project_tree()

    def add_task(self):
        if not self.store: return
        d = TaskDialog(self)
        if d.exec() != QDialog.Accepted: return
        values = d.values()
        if not values['title']:
            QMessageBox.warning(self,'업무 내용','업무 내용을 입력하세요.'); return
        values.update({'task_id':uuid4().hex,'status':'진행중','completed_at':'','created_at':now(),'updated_at':now()})
        self.store.tasks.append(values); self.store.save(); self.refresh()

    def selected_task(self):
        row = self.table.currentRow()
        if row < 0: return None
        item = self.table.item(row,1)
        return next((t for t in self.store.tasks if t['task_id']==item.data(Qt.UserRole)), None)

    def on_task_double_click(self, index):
        self.edit_task()

    def open_selected_task_source(self):
        task=self.selected_task()
        if not task:
            QMessageBox.information(self,'업무 선택','먼저 업무를 선택하세요.'); return
        meeting_id=task.get('source_meeting_id')
        if not meeting_id:
            QMessageBox.information(self,'연결 정보 없음','직접 등록한 업무입니다. 연결된 원본 회의록이 없습니다.'); return
        self.open_meetings(meeting_id)

    def edit_task(self):
        if not self.store: return
        task = self.selected_task()
        if not task: return
        d = TaskDialog(self, task)
        if d.exec() != QDialog.Accepted: return
        values = d.values()
        if not values['title']: return
        task.update(values); task['updated_at']=now(); self.store.save(); self.refresh()

    def delete_task(self):
        task = self.selected_task()
        if not task: return
        if QMessageBox.question(self,'업무 삭제','선택한 업무를 휴지통으로 이동할까요?') != QMessageBox.Yes: return
        self.store.tasks.remove(task); task['deleted_at']=now(); self.store.trash.append(task); self.store.save(); self.refresh()

    def set_completed(self, task_id, checked):
        task = next((t for t in self.store.tasks if t['task_id']==task_id),None)
        if not task: return
        task['status'] = '완료' if checked else '진행중'
        task['completed_at'] = now() if checked else ''
        task['updated_at'] = now(); self.store.save(); self.refresh()

    def refresh(self):
        if not self.store:return
        self.table.setSortingEnabled(False);q=self.search.text().strip().lower();tasks=[t for t in self.store.tasks if not q or q in (t.get('title','')+' '+t.get('owner','')).lower()]
        if self.current_view=='진행중':tasks=[t for t in tasks if t.get('status')!='완료']
        elif self.current_view=='완료 업무':tasks=[t for t in tasks if t.get('status')=='완료']
        if self.incomplete.isChecked():tasks=[t for t in tasks if t.get('status')!='완료']
        self.table.setRowCount(len(tasks));priority_order={'높음':0,'중간':1,'낮음':2}
        for r,t in enumerate(tasks):
            tid=t.get('task_id');checked=t.get('status')=='완료';check=QToolButton();check.setObjectName('completeBox');check.setCheckable(True);check.setChecked(checked);check.setText('☑' if checked else '☐');check.toggled.connect(lambda state,task_id=tid,b=check:(b.setText('☑' if state else '☐'),self.set_completed(task_id,state)))
            holder=QWidget();holder.setStyleSheet('background:transparent;');hl=QHBoxLayout(holder);hl.setContentsMargins(0,0,0,0);hl.addStretch();hl.addWidget(check);hl.addStretch();self.table.setCellWidget(r,0,holder)
            start_date=t.get('start_date') or (t.get('created_at') or '')[:10];due=t.get('due') or '미정';completed=(t.get('completed_at') or '')[:10]
            values=[t.get('title',''),t.get('owner') or '미정',start_date,due,t.get('priority','중간'),t.get('status','진행중'),completed];keys=[values[0].lower(),values[1].lower(),start_date or '9999',due if due!='미정' else '9999',priority_order.get(values[4],9),0 if values[5]!='완료' else 1,completed or '9999']
            for c,(v,key) in enumerate(zip(values,keys),1):
                item=SortableItem(v,key);item.setData(Qt.UserRole,tid);item.setTextAlignment(Qt.AlignLeft|Qt.AlignVCenter if c==1 else Qt.AlignCenter);item.setToolTip(str(v));self.table.setItem(r,c,item)
        all_t=self.store.tasks;done_n=sum(t.get('status')=='완료' for t in all_t);self.total[1].setText(str(len(all_t)));self.active[1].setText(str(len(all_t)-done_n));self.done[1].setText(str(done_n));self.update_project_summary();self.table.setSortingEnabled(True)

    def update_project_summary(self):
        if not self.store:return
        total=len(self.store.tasks); incomplete=sum(t.get('status')!='완료' for t in self.store.tasks); code=self.store.meta.get('code','').strip(); name=self.store.meta.get('name',self.current_folder.name).strip(); display=f'{code} {name}'.strip()
        for i in range(self.project_tree.topLevelItemCount()):
            item=self.project_tree.topLevelItem(i)
            if item.data(0,Qt.UserRole)==str(self.current_folder): item.setText(0,f'{display}\n업무 {total} · 미완료 {incomplete}'); break

    def collect_global_spec_changes(self):
        rows=[]
        DATA_ROOT.mkdir(parents=True,exist_ok=True)
        for folder in sorted([p for p in DATA_ROOT.iterdir() if p.is_dir()]):
            meta=ProjectStore._load(folder/'project.json',{'name':folder.name,'code':''})
            project_name=(meta.get('name') or folder.name).strip(); code=(meta.get('code') or '').strip()
            display=f'{code} {project_name}'.strip() if code else project_name
            for spec in ProjectStore._load(folder/'spec_changes.json',[]):
                rows.append({'folder':folder,'project':display,'spec':spec})
        return rows

    def open_global_spec_changes(self):
        d=QDialog(self); d.setWindowTitle('사양 변경 모아보기'); d.resize(1180,680); lay=QVBoxLayout(d)
        title=QLabel('전체 프로젝트 사양 변경'); title.setObjectName('title'); title.setStyleSheet('font-size:15pt;'); lay.addWidget(title)
        filters=QHBoxLayout(); project_filter=QComboBox(); project_filter.addItem('전체 프로젝트'); search=QLineEdit(); search.setPlaceholderText('변경 제목, 변경 전·후 내용 검색'); captured=QCheckBox('캡처 있음만')
        all_rows=self.collect_global_spec_changes(); projects=sorted({x['project'] for x in all_rows})
        project_filter.addItems(projects); filters.addWidget(QLabel('프로젝트')); filters.addWidget(project_filter); filters.addWidget(search,1); filters.addWidget(captured); lay.addLayout(filters)
        table=QTableWidget(0,6); table.setHorizontalHeaderLabels(['프로젝트','변경일','변경 제목','변경 전','변경 후','캡처']); table.setSelectionBehavior(QTableWidget.SelectRows); table.setSelectionMode(QTableWidget.SingleSelection); table.setEditTriggers(QTableWidget.NoEditTriggers); table.verticalHeader().setVisible(False)
        table.horizontalHeader().setSectionResizeMode(0,QHeaderView.ResizeToContents); table.horizontalHeader().setSectionResizeMode(1,QHeaderView.ResizeToContents); table.horizontalHeader().setSectionResizeMode(2,QHeaderView.Stretch); table.horizontalHeader().setSectionResizeMode(3,QHeaderView.Stretch); table.horizontalHeader().setSectionResizeMode(4,QHeaderView.Stretch); table.horizontalHeader().setSectionResizeMode(5,QHeaderView.ResizeToContents); lay.addWidget(table,1)
        def filtered_rows():
            selected=project_filter.currentText(); q=search.text().strip().lower(); result=[]
            for row in self.collect_global_spec_changes():
                spec=row['spec']
                if selected!='전체 프로젝트' and row['project']!=selected: continue
                if captured.isChecked() and not spec.get('attachments'): continue
                text=' '.join(str(spec.get(k,'')) for k in ('title','before','after')).lower()
                if q and q not in text: continue
                result.append(row)
            return sorted(result,key=lambda x:x['spec'].get('change_date',''),reverse=True)
        def reload():
            rows=filtered_rows(); table.setRowCount(len(rows))
            for r,row in enumerate(rows):
                spec=row['spec']; vals=[row['project'],spec.get('change_date',''),spec.get('title',''),spec.get('before',''),spec.get('after',''),str(len(spec.get('attachments',[])))]
                for c,v in enumerate(vals):
                    item=QTableWidgetItem(str(v)); item.setData(Qt.UserRole,{'folder':str(row['folder']),'spec_id':spec.get('spec_id')}); item.setToolTip(str(v)); table.setItem(r,c,item)
            table.resizeRowsToContents()
        def selected_ref():
            r=table.currentRow()
            return table.item(r,0).data(Qt.UserRole) if r>=0 and table.item(r,0) else None
        def edit_selected():
            ref=selected_ref()
            if not ref: return
            folder=Path(ref['folder']); store=ProjectStore(folder); item=next((x for x in store.spec_changes if x.get('spec_id')==ref['spec_id']),None)
            if not item:return
            dialog=SpecChangeDialog(d,item,project_folder=folder)
            if dialog.exec()!=QDialog.Accepted:return
            item.update(dialog.values()); item['updated_at']=now(); item.pop('requester',None); store.save(); reload(); self.reload_project_tree()
        def open_project_record():
            ref=selected_ref()
            if not ref:return
            folder=Path(ref['folder']); self.open_project(folder); d.accept(); self.open_spec_changes(ref.get('spec_id'))
        def delete_selected():
            ref=selected_ref()
            if not ref:return
            if QMessageBox.question(d,'사양 변경 삭제','선택 기록을 삭제할까요?')!=QMessageBox.Yes:return
            folder=Path(ref['folder']); store=ProjectStore(folder); store.spec_changes=[x for x in store.spec_changes if x.get('spec_id')!=ref['spec_id']]; store.save(); reload()
        buttons=QHBoxLayout(); edit=QPushButton('선택 수정'); open_project=QPushButton('프로젝트에서 열기'); delete=QPushButton('선택 삭제'); close=QPushButton('닫기'); edit.clicked.connect(edit_selected); open_project.clicked.connect(open_project_record); delete.clicked.connect(delete_selected); close.clicked.connect(d.accept); buttons.addWidget(edit); buttons.addWidget(open_project); buttons.addWidget(delete); buttons.addStretch(); buttons.addWidget(close); lay.addLayout(buttons)
        project_filter.currentTextChanged.connect(reload); search.textChanged.connect(reload); captured.toggled.connect(reload); table.doubleClicked.connect(edit_selected); reload(); d.exec()

    def open_spec_changes(self, focus_spec_id=None):
        if not self.store:return
        d=QDialog(self); d.setWindowTitle(f'사양 변경 · {self.store.meta.get("name",self.current_folder.name)}'); d.resize(1050,600); lay=QVBoxLayout(d)
        info=QLabel('프로젝트 진행 중 변경된 요구사항과 화면·동작을 기록합니다.'); info.setObjectName('hint'); lay.addWidget(info)
        search=QLineEdit(); search.setPlaceholderText('변경 제목 또는 변경 내용 검색'); lay.addWidget(search)
        table=QTableWidget(0,4); table.setHorizontalHeaderLabels(['변경일','변경 제목','변경 후','캡처']); table.setSelectionBehavior(QTableWidget.SelectRows); table.setSelectionMode(QTableWidget.SingleSelection); table.setEditTriggers(QTableWidget.NoEditTriggers); table.verticalHeader().setVisible(False)
        table.horizontalHeader().setSectionResizeMode(0,QHeaderView.ResizeToContents); table.horizontalHeader().setSectionResizeMode(1,QHeaderView.Stretch); table.horizontalHeader().setSectionResizeMode(2,QHeaderView.Stretch); table.horizontalHeader().setSectionResizeMode(3,QHeaderView.ResizeToContents); lay.addWidget(table,1)
        def filtered():
            q=search.text().strip().lower(); return [x for x in self.store.spec_changes if not q or q in json.dumps(x,ensure_ascii=False).lower()]
        def reload():
            rows=sorted(filtered(),key=lambda x:x.get('change_date',''),reverse=True); table.setRowCount(len(rows))
            for r,x in enumerate(rows):
                vals=[x.get('change_date',''),x.get('title',''),x.get('after',''),str(len(x.get('attachments',[])))]
                for c,v in enumerate(vals): item=QTableWidgetItem(v); item.setData(Qt.UserRole,x.get('spec_id')); item.setToolTip(v); table.setItem(r,c,item)
            table.resizeRowsToContents()
        def current():
            r=table.currentRow()
            if r<0 or not table.item(r,0):return None
            sid=table.item(r,0).data(Qt.UserRole); return next((x for x in self.store.spec_changes if x.get('spec_id')==sid),None)
        def add():
            x=SpecChangeDialog(d,project_folder=self.store.folder)
            if x.exec()!=QDialog.Accepted:return
            v=x.values();v.update({'spec_id':uuid4().hex,'created_at':now(),'updated_at':now()});self.store.spec_changes.append(v);self.store.save();reload()
        def edit():
            item=current()
            if not item:return
            x=SpecChangeDialog(d,item,project_folder=self.store.folder)
            if x.exec()!=QDialog.Accepted:return
            item.update(x.values());item.pop('requester',None);item['updated_at']=now();self.store.save();reload()
        def remove():
            item=current()
            if item and QMessageBox.question(d,'사양 변경 삭제','선택 기록을 삭제할까요?')==QMessageBox.Yes:self.store.spec_changes.remove(item);self.store.save();reload()
        row=QHBoxLayout();a=QPushButton('+ 사양 변경 등록');a.setObjectName('primary');e=QPushButton('선택 수정');x=QPushButton('선택 삭제');close=QPushButton('닫기');a.clicked.connect(add);e.clicked.connect(edit);x.clicked.connect(remove);close.clicked.connect(d.accept);row.addWidget(a);row.addWidget(e);row.addWidget(x);row.addStretch();row.addWidget(close);lay.addLayout(row)
        search.textChanged.connect(reload);table.doubleClicked.connect(edit);reload()
        if focus_spec_id:
            for r in range(table.rowCount()):
                if table.item(r,0) and table.item(r,0).data(Qt.UserRole)==focus_spec_id: table.selectRow(r); table.scrollToItem(table.item(r,0)); break
        d.exec()

    def open_meetings(self, focus_meeting_id=None):
        if not self.store:return
        d=QDialog(self); d.setWindowTitle(f'회의록 · {self.store.meta.get("name",self.current_folder.name)}'); d.resize(900,550); lay=QVBoxLayout(d); search=QLineEdit(); search.setPlaceholderText('회의록 검색'); lay.addWidget(search)
        table=QTableWidget(0,5); table.setHorizontalHeaderLabels(['회의일','회의 제목','참석자','후속 조치','캡처']); table.horizontalHeader().setSectionResizeMode(1,QHeaderView.Stretch); table.horizontalHeader().setSectionResizeMode(3,QHeaderView.Stretch); table.horizontalHeader().setSectionResizeMode(4,QHeaderView.ResizeToContents); table.setSelectionBehavior(QTableWidget.SelectRows); table.setEditTriggers(QTableWidget.NoEditTriggers); lay.addWidget(table,1)
        def rows():
            q=search.text().strip().lower(); return [m for m in self.store.meetings if not q or q in json.dumps(m,ensure_ascii=False).lower()]
        def reload():
            data=sorted(rows(),key=lambda m:m.get('meeting_date',''),reverse=True); table.setRowCount(len(data))
            for r,m in enumerate(data):
                for c,v in enumerate([m.get('meeting_date',''),m.get('title',''),m.get('attendees',''),m.get('actions',''),str(len(m.get('attachments',[])))]): it=QTableWidgetItem(v); it.setData(Qt.UserRole,m.get('meeting_id')); table.setItem(r,c,it)
        def current():
            r=table.currentRow(); return next((m for m in self.store.meetings if r>=0 and table.item(r,0) and m.get('meeting_id')==table.item(r,0).data(Qt.UserRole)),None)
        def add():
            x=MeetingDialog(d,project_folder=self.store.folder)
            if x.exec()!=QDialog.Accepted:return
            v=x.values()
            if not v['title']:return
            v.update({'meeting_id':uuid4().hex,'created_at':now(),'updated_at':now()}); self.store.meetings.append(v); self.store.save(); reload()
        def edit():
            m=current()
            if not m:return
            x=MeetingDialog(d,m,project_folder=self.store.folder)
            if x.exec()!=QDialog.Accepted:return
            m.update(x.values()); m['updated_at']=now(); self.store.save(); reload()
        def remove():
            m=current()
            if m and QMessageBox.question(d,'회의록 삭제','선택 회의록을 삭제할까요?')==QMessageBox.Yes:self.store.meetings.remove(m);self.store.save();reload()
        def task():
            m=current()
            if not m:return
            self.store.tasks.append({'task_id':uuid4().hex,'title':f'[회의 후속] {m.get("title","")}','owner':'','start_date':date.today().isoformat(),'due':'','priority':'중간','status':'진행중','completed_at':'','source_meeting_id':m.get('meeting_id'),'created_at':now()}); self.store.save(); self.refresh(); QMessageBox.information(d,'등록 완료','원본 회의록과 연결된 후속 업무로 등록했습니다.')
        row=QHBoxLayout(); a=QPushButton('+ 새 회의록'); a.setObjectName('primary'); e=QPushButton('수정'); t=QPushButton('후속 업무 등록'); x=QPushButton('삭제'); close=QPushButton('닫기'); a.clicked.connect(add);e.clicked.connect(edit);t.clicked.connect(task);x.clicked.connect(remove);close.clicked.connect(d.accept)
        for b in (a,e,t,x):row.addWidget(b)
        row.addStretch();row.addWidget(close);lay.addLayout(row);search.textChanged.connect(reload);table.doubleClicked.connect(edit);reload()
        if focus_meeting_id:
            for r in range(table.rowCount()):
                if table.item(r,0) and table.item(r,0).data(Qt.UserRole)==focus_meeting_id: table.selectRow(r);table.scrollToItem(table.item(r,0));break
        d.exec()

    def open_trash(self):
        if not self.store: return
        d=QDialog(self); d.setWindowTitle('휴지통'); d.resize(650,420); lay=QVBoxLayout(d)
        table=QTableWidget(0,3); table.setHorizontalHeaderLabels(['업무 내용','삭제일','담당자']); table.horizontalHeader().setSectionResizeMode(0,QHeaderView.Stretch); table.setSelectionBehavior(QTableWidget.SelectRows); table.setEditTriggers(QTableWidget.NoEditTriggers); lay.addWidget(table)
        def reload():
            table.setRowCount(len(self.store.trash))
            for r,t in enumerate(self.store.trash):
                for c,v in enumerate([t.get('title',''),(t.get('deleted_at') or '')[:10],t.get('owner') or '미정']):
                    it=QTableWidgetItem(v); it.setData(Qt.UserRole,t['task_id']); it.setTextAlignment(Qt.AlignCenter); table.setItem(r,c,it)
        def current():
            row=table.currentRow(); return next((t for t in self.store.trash if row>=0 and t['task_id']==table.item(row,0).data(Qt.UserRole)),None)
        def restore():
            t=current()
            if t: self.store.trash.remove(t); t.pop('deleted_at',None); self.store.tasks.append(t); self.store.save(); reload(); self.refresh()
        def erase():
            t=current()
            if t and QMessageBox.question(d,'영구 삭제','되돌릴 수 없습니다. 삭제할까요?')==QMessageBox.Yes: self.store.trash.remove(t); self.store.save(); reload()
        row=QHBoxLayout(); a=QPushButton('선택 복원'); b=QPushButton('선택 영구 삭제'); c=QPushButton('닫기'); a.clicked.connect(restore); b.clicked.connect(erase); c.clicked.connect(d.accept); row.addWidget(a); row.addWidget(b); row.addStretch(); row.addWidget(c); lay.addLayout(row); reload(); d.exec()

    def export_excel(self):
        if not self.store: return
        try:
            from openpyxl import Workbook
        except ImportError:
            QMessageBox.warning(self,'패키지 필요','openpyxl 설치가 필요합니다.'); return
        p,_=QFileDialog.getSaveFileName(self,'Excel 저장',str(self.current_folder/'업무목록.xlsx'),'Excel (*.xlsx)')
        if not p:return
        wb=Workbook(); ws=wb.active; ws.title='업무 목록'; ws.append(['완료','업무 내용','담당자','시작일','마감일','중요도','상태','완료일'])
        for t in self.store.tasks: ws.append(['Y' if t.get('status')=='완료' else '',t.get('title',''),t.get('owner',''),t.get('start_date',''),t.get('due',''),t.get('priority',''),t.get('status',''),(t.get('completed_at') or '')[:10]])
        wb.save(p); QMessageBox.information(self,'저장 완료','Excel 파일을 저장했습니다.')


if __name__ == '__main__':
    app=QApplication(sys.argv); w=SimpleWorkbench(); w.show(); sys.exit(app.exec())
