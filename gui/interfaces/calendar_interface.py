import os
from PySide6.QtCore import Qt, QDate
from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QCalendarWidget, 
                             QInputDialog, QListWidget, QListWidgetItem)
from qfluentwidgets import (SubtitleLabel, TitleLabel, PrimaryPushButton, TransparentPushButton, 
                            IconWidget, FluentIcon as FIF, ScrollArea, BodyLabel, CardWidget)

from core.database import insert_event, get_events_for_date

class EventCard(CardWidget):
    def __init__(self, event_dict, parent=None):
        super().__init__(parent)
        self.setFixedHeight(80)
        self.setStyleSheet("""
            EventCard {
                background: rgba(0, 0, 0, 0.5);
                border: 1px solid rgba(255, 255, 255, 0.1);
                border-radius: 10px;
            }
        """)
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(15, 10, 15, 10)
        
        self.title = BodyLabel(event_dict['title'])
        self.title.setStyleSheet("font-size: 16px; font-weight: bold; color: white;")
        layout.addWidget(self.title)
        
        if event_dict.get('description'):
            desc = BodyLabel(event_dict['description'])
            desc.setStyleSheet("font-size: 12px; color: #aaa;")
            layout.addWidget(desc)

class CalendarInterface(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent=parent)
        self.setObjectName("CalendarInterface")
        self.setStyleSheet("background: transparent;")
        
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(40, 40, 40, 40)
        self.layout.setSpacing(20)
        
        # Header
        header = QHBoxLayout()
        self.title = TitleLabel("Study Calendar", self)
        header.addWidget(self.title)
        header.addStretch(1)
        
        self.btn_add = PrimaryPushButton(FIF.ADD, "Add Event", self)
        self.btn_add.clicked.connect(self.add_event_dialog)
        header.addWidget(self.btn_add)
        
        self.layout.addLayout(header)
        
        # Content Area (Horizontal)
        content_layout = QHBoxLayout()
        content_layout.setSpacing(30)
        
        # Left: Calendar
        self.calendar = QCalendarWidget()
        self.calendar.setGridVisible(True)
        self.calendar.setVerticalHeaderFormat(QCalendarWidget.NoVerticalHeader)
        self.calendar.setStyleSheet("""
            QCalendarWidget {
                background-color: rgba(0, 0, 0, 0.3);
                color: white;
                border: 1px solid rgba(255, 255, 255, 0.1);
                border-radius: 10px;
            }
            QCalendarWidget QAbstractItemView:enabled {
                color: white;
                background-color: transparent;
                selection-background-color: #0078d7;
                selection-color: white;
            }
            QCalendarWidget QWidget#qt_calendar_navigationbar {
                background-color: rgba(0, 0, 0, 0.5);
            }
        """)
        self.calendar.selectionChanged.connect(self.update_event_list)
        content_layout.addWidget(self.calendar, 2)
        
        # Right: Events list
        self.events_view = QWidget()
        ev_layout = QVBoxLayout(self.events_view)
        ev_layout.setContentsMargins(0, 0, 0, 0)
        
        self.selected_date_label = SubtitleLabel("Events")
        ev_layout.addWidget(self.selected_date_label)
        
        self.scroll_area = ScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setStyleSheet("background: transparent; border: none;")
        
        self.list_container = QWidget()
        self.list_container.setStyleSheet("background: transparent;")
        self.list_layout = QVBoxLayout(self.list_container)
        self.list_layout.setAlignment(Qt.AlignTop)
        self.list_layout.setSpacing(10)
        
        self.scroll_area.setWidget(self.list_container)
        ev_layout.addWidget(self.scroll_area)
        
        content_layout.addWidget(self.events_view, 1)
        
        self.layout.addLayout(content_layout)
        
        # Initial load
        self.update_event_list()

    def update_event_list(self):
        date = self.calendar.selectedDate().toString("yyyy-MM-dd")
        display_date = self.calendar.selectedDate().toString("MMMM d, yyyy")
        self.selected_date_label.setText(f"Events on {display_date}")
        
        # Clear existing
        for i in reversed(range(self.list_layout.count())):
            widget = self.list_layout.itemAt(i).widget()
            if widget:
                widget.deleteLater()
                
        events = get_events_for_date(date)
        if not events:
            empty = BodyLabel("No events scheduled.")
            empty.setStyleSheet("color: #666; font-style: italic;")
            self.list_layout.addWidget(empty)
        else:
            for ev in events:
                card = EventCard(ev)
                self.list_layout.addWidget(card)

    def add_event_dialog(self):
        title, ok = QInputDialog.getText(self, "New Event", "Event Title:")
        if ok and title:
            date = self.calendar.selectedDate().toString("yyyy-MM-dd")
            insert_event(date, title)
            self.update_event_list()
            # Trigger home update if needed (will happen on next home show)
