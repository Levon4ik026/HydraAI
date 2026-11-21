import sys, csv, subprocess, urllib.request, json
from pathlib import Path
from datetime import datetime, timezone, timedelta
from PySide6.QtCore import Qt, QTimer, QProcess, QProcessEnvironment
from PySide6.QtGui import QColor, QPainter, QPen, QFont, QIcon
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QFrame, QStackedWidget, QTextEdit, QGridLayout, QMessageBox,
    QSizePolicy, QTabWidget, QInputDialog, QLineEdit
)
from hydra_data_quality import load_and_check
from hydra_strategy_core import analyze_candles
from hydra_demo.engine import Candle as DemoCandle
from hydra_demo.runtime import CandidateMonitor

if getattr(sys, "frozen", False):
    BASE = Path(sys.executable).resolve().parents[1]
else:
    BASE = Path(__file__).resolve().parent
DATA = BASE / 'observer_data' / 'eurusd_guest_candles.csv'
AI_LOG = BASE / 'observer_data' / 'ai_analysis_log.txt'

DARK = '#0b1018'
PANEL = '#121b28'
PANEL2 = '#172333'
BORDER = '#26364a'
TEXT = '#e8eef7'
MUTED = '#91a1b5'
CYAN = '#54d6e8'
GREEN = '#45d69a'
RED = '#ff6b78'
AMBER = '#f2bd62'

class CandleChart(QWidget):
    def __init__(self):
        super().__init__(); self.setMinimumHeight(300)
        self.candles=[]
    def set_candles(self, candles, live_candle=None):
        self.candles = list(candles[-200:])
        if live_candle is not None:
            if not self.candles or live_candle["time"] > self.candles[-1]["time"]:
                self.candles.append(live_candle)
            elif live_candle["time"] == self.candles[-1]["time"]:
                self.candles[-1] = live_candle
        self.candles = self.candles[-200:]
        self.update()
    def paintEvent(self, event):
        p=QPainter(self); p.setRenderHint(QPainter.Antialiasing)
        p.fillRect(self.rect(), QColor('#0e1621'))
        r=self.rect().adjusted(48,18,16,28)
        p.setPen(QPen(QColor('#1e2a39'),1,Qt.PenStyle.DashLine))
        for i in range(5):
            y=r.top()+i*r.height()/4; p.drawLine(r.left(),int(y),r.right(),int(y))
        if len(self.candles)<2:
            p.setPen(QColor(MUTED)); p.drawText(r,Qt.AlignmentFlag.AlignCenter,'Ожидаю проверенные свечи EUR/USD'); return
        lo=min(float(c['low']) for c in self.candles); hi=max(float(c['high']) for c in self.candles)
        if hi<=lo: hi=lo+0.0001
        pad=(hi-lo)*0.08; lo-=pad; hi+=pad
        p.setFont(QFont('Segoe UI',8)); p.setPen(QColor(MUTED))
        for i in range(5):
            val=hi-(hi-lo)*i/4; y=r.top()+r.height()*i/4
            p.drawText(2,int(y-7),42,15,Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter,f'{val:.5f}')
        n=len(self.candles); step=r.width()/n; body=max(3,min(10,step*.58))
        for i,c in enumerate(self.candles):
            x=r.left()+step*(i+.5)
            y=lambda v: r.bottom()-(float(v)-lo)/(hi-lo)*r.height()
            up=float(c['close'])>=float(c['open']); col=QColor(GREEN if up else RED)
            p.setPen(QPen(col,1.2)); p.drawLine(int(x),int(y(c['high'])),int(x),int(y(c['low'])))
            top=min(y(c['open']),y(c['close'])); bot=max(y(c['open']),y(c['close']))
            p.fillRect(int(x-body/2),int(top),max(2,int(body)),max(2,int(bot-top)),col)
        p.setPen(QColor(MUTED)); p.drawText(r.left(),self.height()-7, 'Старые свечи слева  •  новые справа')

class MetricCard(QFrame):
    def __init__(self, title, value='—', note=''):
        super().__init__(); self.setObjectName('panel')
        l=QVBoxLayout(self); l.setContentsMargins(16,13,16,13); l.setSpacing(5)
        self.t=QLabel(title); self.t.setObjectName('muted')
        self.v=QLabel(value); self.v.setObjectName('metric')
        self.n=QLabel(note); self.n.setObjectName('muted'); self.n.setWordWrap(True)
        l.addWidget(self.t); l.addWidget(self.v); l.addWidget(self.n)
    def set(self,value,note=None):
        self.v.setText(str(value))
        if note is not None: self.n.setText(note)

class HydraWindow(QMainWindow):
    def __init__(self):
        super().__init__(); self.setWindowTitle('HYDRA AI  •  Терминал EUR/USD'); self.resize(1440,900); self.setMinimumSize(1100,720)
        self.observer=QProcess(self); self.observer.setWorkingDirectory(str(BASE)); self.observer.readyReadStandardOutput.connect(self.read_observer); self.observer.readyReadStandardError.connect(self.read_observer_err); self.observer.finished.connect(self.observer_finished)
        self.ai=QProcess(self); self.ai.setWorkingDirectory(str(BASE)); self.ai.readyReadStandardOutput.connect(self.read_ai); self.ai.readyReadStandardError.connect(self.read_ai_err); self.ai.finished.connect(self.ai_finished)
        self.mode='LIGHT'; self.last_quality=None
        self.candidate_monitor = CandidateMonitor(BASE / 'observer_data', payout=0.92)
        self.last_adaptive_result = None
        self.live_price = None
        self.live_candle = None
        self.connection_status = "STOPPED"
        self.observer_stdout_buffer = ''
        self.execution_worker = QProcess(self)
        self.execution_worker.setWorkingDirectory(str(BASE))
        self.execution_worker.readyReadStandardOutput.connect(self.read_execution_output)
        self.execution_worker.readyReadStandardError.connect(self.read_execution_error)
        self.execution_worker.finished.connect(self.execution_finished)
        self.demo_autotrade_enabled = False
        self.execution_stdout_buffer = ''
        self.last_live_signal_minute = None
        self.demo_eligible_candidates = None
        self.build_ui(); self.apply_style()
        self.timer=QTimer(self); self.timer.timeout.connect(self.refresh_data); self.timer.start(4000); self.refresh_data(); self.check_ollama()
    def build_ui(self):
        root=QWidget(); self.setCentralWidget(root); outer=QVBoxLayout(root); outer.setContentsMargins(22,18,22,18); outer.setSpacing(14)
        header=QHBoxLayout(); brand=QVBoxLayout(); name=QLabel('HYDRA'); name.setObjectName('brand'); sub=QLabel('ИНТЕЛЛЕКТУАЛЬНЫЙ АНАЛИЗ РЫНКА  /  EUR·USD'); sub.setObjectName('muted'); brand.addWidget(name); brand.addWidget(sub); header.addLayout(brand); header.addStretch()
        self.market_badge=QLabel('● РЫНОК: ОЖИДАНИЕ'); self.market_badge.setObjectName('badge'); header.addWidget(self.market_badge)
        self.light_btn=QPushButton('LIGHT'); self.pro_btn=QPushButton('PRO'); self.light_btn.clicked.connect(lambda:self.set_mode('LIGHT')); self.pro_btn.clicked.connect(lambda:self.set_mode('PRO')); header.addWidget(self.light_btn); header.addWidget(self.pro_btn)
        outer.addLayout(header)
        bar=QHBoxLayout(); self.price=MetricCard('EUR/USD • ПОСЛЕДНЯЯ ЦЕНА'); self.feed=MetricCard('ПОТОК ДАННЫХ','ОСТАНОВЛЕН','Подключение DEMO'); self.quality=MetricCard('КАЧЕСТВО ДАННЫХ','НЕТ ДАННЫХ','Проверка CSV'); self.candles_count=MetricCard('СВЕЧИ','0','В файле наблюдателя')
        for w in [self.price,self.feed,self.quality,self.candles_count]: bar.addWidget(w)
        outer.addLayout(bar)
        self.stack=QStackedWidget(); outer.addWidget(self.stack,1)
        self.light_page=QWidget(); ll=QVBoxLayout(self.light_page); ll.setContentsMargins(0,0,0,0); ll.setSpacing(12)
        self.signal_panel=QFrame(); self.signal_panel.setObjectName('signal'); sl=QVBoxLayout(self.signal_panel); sl.setContentsMargins(22,18,22,18)
        self.signal_title=QLabel('СПРАВОЧНЫЙ СИГНАЛ ТЕХНИЧЕСКОГО ЯДРА'); self.signal_title.setObjectName('muted'); self.signal=QLabel('ОЖИДАНИЕ'); self.signal.setObjectName('signalText'); self.signal_note=QLabel('Сигнальная стратегия CALL/PUT ещё не реализована и не прошла проверку.'); self.signal_note.setObjectName('muted'); self.signal_note.setWordWrap(True); sl.addWidget(self.signal_title); sl.addWidget(self.signal); sl.addWidget(self.signal_note); ll.addWidget(self.signal_panel)
        self.chart=CandleChart(); self.chart.setObjectName('panel'); ll.addWidget(self.chart,1)
        lower=QHBoxLayout(); self.trend=MetricCard('НАБЛЮДАЕМОЕ ДВИЖЕНИЕ','—','По последним проверенным свечам'); self.last_candle=MetricCard('ПОСЛЕДНЯЯ СВЕЧА UTC','—','Время последней записи'); self.ai_status=MetricCard('ЛОКАЛЬНЫЙ ИИ','НЕ ПРОВЕРЕН','Ollama / Qwen 2.5 7B'); self.adaptive_status=MetricCard('АДАПТИВНЫЙ ОТБОР','WAIT','Пять кандидатов • только наблюдение'); lower.addWidget(self.trend); lower.addWidget(self.last_candle); lower.addWidget(self.ai_status); lower.addWidget(self.adaptive_status); ll.addLayout(lower)
        self.stack.addWidget(self.light_page)
        self.pro_page=QWidget(); pl=QVBoxLayout(self.pro_page); pl.setContentsMargins(0,0,0,0)
        self.tabs=QTabWidget(); pl.addWidget(self.tabs)
        overview=QWidget(); ol=QVBoxLayout(overview); grid=QGridLayout(); self.m5=MetricCard('ИЗМЕНЕНИЕ • 5 МИН','—'); self.m15=MetricCard('ИЗМЕНЕНИЕ • 15 МИН','—'); self.m30=MetricCard('ИЗМЕНЕНИЕ • 30 МИН','—'); self.vol=MetricCard('СРЕДНИЙ ДИАПАЗОН','—'); self.gaps=MetricCard('РАЗРЫВЫ В ИСТОРИИ','—'); self.age=MetricCard('ВОЗРАСТ ПОСЛЕДНЕЙ СВЕЧИ','—');
        for i,w in enumerate([self.m5,self.m15,self.m30,self.vol,self.gaps,self.age]): grid.addWidget(w,i//3,i%3)
        ol.addLayout(grid); self.pro_chart=CandleChart(); ol.addWidget(self.pro_chart,1); self.tabs.addTab(overview,'Обзор')
        ai_tab=QWidget(); al=QVBoxLayout(ai_tab); self.ai_output=QTextEdit(); self.ai_output.setReadOnly(True); self.ai_output.setPlaceholderText('Здесь появится результат проверки и локального ИИ-анализа.'); al.addWidget(self.ai_output); self.tabs.addTab(ai_tab,'ИИ-анализ')
        log_tab=QWidget(); logl=QVBoxLayout(log_tab); self.log_output=QTextEdit(); self.log_output.setReadOnly(True); logl.addWidget(self.log_output); self.tabs.addTab(log_tab,'Журнал')
        self.stack.addWidget(self.pro_page)
        controls=QHBoxLayout(); self.start_btn=QPushButton('▶  ЗАПУСТИТЬ СБОР ДАННЫХ'); self.start_btn.clicked.connect(self.toggle_observer); self.analyze_btn=QPushButton('✦  ЗАПУСТИТЬ ИИ-АНАЛИЗ'); self.analyze_btn.clicked.connect(self.run_ai); self.analyze_btn.setObjectName('primary'); self.open_data_btn=QPushButton('ОТКРЫТЬ ПАПКУ ДАННЫХ'); self.open_data_btn.clicked.connect(lambda:subprocess.Popen(['explorer',str(DATA.parent)])); self.demo_btn = QPushButton('DEMO АВТО: ВЫКЛ'); self.demo_btn.clicked.connect(self.toggle_demo_autotrade)
        controls.addWidget(self.start_btn); controls.addWidget(self.analyze_btn); controls.addWidget(self.demo_btn); controls.addStretch(); controls.addWidget(self.open_data_btn); outer.addLayout(controls)
        footer=QHBoxLayout(); self.footer=QLabel('АНАЛИЗ + DEMO ПО ЯВНОМУ РАЗРЕШЕНИЮ  •  REAL И OTC ЗАПРЕЩЕНЫ'); self.footer.setObjectName('muted'); self.connection=QLabel('Подключение: не запущено'); self.connection.setObjectName('muted'); footer.addWidget(self.footer); footer.addStretch(); footer.addWidget(self.connection); outer.addLayout(footer)
    def apply_style(self):
        self.setStyleSheet(f'''QMainWindow,QWidget{{background:{DARK};color:{TEXT};font-family:"Segoe UI";font-size:13px}} QFrame#panel,QFrame#signal{{background:{PANEL};border:1px solid {BORDER};border-radius:14px}} QLabel#brand{{font-size:30px;font-weight:800;letter-spacing:5px;color:{CYAN}}} QLabel#muted{{color:{MUTED};font-size:11px}} QLabel#metric{{font-size:24px;font-weight:700;color:{TEXT}}} QLabel#badge{{background:{PANEL2};border:1px solid {BORDER};border-radius:10px;padding:9px 13px;color:{AMBER};font-weight:700}} QLabel#signalText{{font-size:36px;font-weight:800;color:{AMBER};padding:4px 0}} QPushButton{{background:{PANEL2};color:{TEXT};border:1px solid {BORDER};border-radius:9px;padding:10px 15px;font-weight:700}} QPushButton:hover{{border-color:{CYAN};color:{CYAN}}} QPushButton#primary{{background:#16445a;border-color:#28718b;color:#eaffff}} QPushButton:disabled{{color:#5f6d7c;background:#111923}} QTabWidget::pane{{border:1px solid {BORDER};border-radius:10px;background:{PANEL}}} QTabBar::tab{{background:{PANEL2};padding:10px 18px;border-top-left-radius:8px;border-top-right-radius:8px;color:{MUTED}}} QTabBar::tab:selected{{background:{PANEL};color:{CYAN}}} QTextEdit{{background:#0e1621;border:1px solid {BORDER};border-radius:10px;padding:12px;color:{TEXT}}}''')
    def set_mode(self,mode): self.mode=mode; self.stack.setCurrentIndex(0 if mode=='LIGHT' else 1); self.light_btn.setStyleSheet('color:'+CYAN if mode=='LIGHT' else ''); self.pro_btn.setStyleSheet('color:'+CYAN if mode=='PRO' else '')
    def log(self,text):
        stamp=datetime.now().strftime('%H:%M:%S'); line=f'[{stamp}] {text}'
        self.log_output.append(line)
    def refresh_data(self):
        try:
            q=load_and_check(DATA)
            self.last_quality=q
            candles=q['candles']; rep=q['report']; self.candles_count.set(rep['rows_total'], 'Строк в исходном CSV')
            self.quality.set(q['status'],f"Ошибок: {rep['rows_invalid']} • Разрывов: {len(rep['gaps'])}")
            if candles:
                last = candles[-1]

                if (self.connection_status == "CONNECTED"
                        and self.live_price is not None):
                    self.price.set(
                        f"{self.live_price:.5f}",
                        "Текущая цена • Pocket Option DEMO"
                    )
                else:
                    self.price.set(
                        f"{last['close']:.5f}",
                        "Последняя цена закрытия"
                    )

                self.last_candle.set(
                    last['time'].strftime('%d.%m.%Y %H:%M UTC')
                )

                live = (
                    self.live_candle
                    if self.connection_status == "CONNECTED"
                    else None
                )
                self.chart.set_candles(candles, live)
                self.pro_chart.set_candles(candles, live)
                age=rep.get('latest_age_seconds'); self.age.set(f'{age/60:.1f} мин' if age is not None else '—')
                self.gaps.set(len(rep['gaps']), 'Разрывы по всей истории')
                if len(candles)>=200:
                    recent=candles[-200:]; continuous=all((b['time']-a['time']).total_seconds()==60 for a,b in zip(recent[:-1],recent[1:]))
                    if q['status']=='FRESH' and continuous:
                        start=recent[0]['close']; end=recent[-1]['close']; pct=(end/start-1)*100 if start else 0
                        direction='Рост' if pct>0 else 'Снижение' if pct<0 else 'Без изменения'
                        self.trend.set(f'{direction}  {pct:+.4f}%', 'Изменение внутри рабочего окна 200 свечей')
                        # Adaptive layer observes only validated, completed CSV candles.
                        try:
                            demo_candles = [DemoCandle(c['time'].astimezone(timezone.utc), float(c['open']), float(c['high']), float(c['low']), float(c['close'])) for c in candles]
                            if len(demo_candles) < 275:
                                self.last_adaptive_result = None
                                self.adaptive_status.set('WAIT', f'Для расчёта всех пяти кандидатов нужно минимум 275 завершённых свечей; сейчас {len(demo_candles)}')
                            else:
                                adaptive = self.candidate_monitor.process(demo_candles, feed_ok=True, completed_candles=demo_candles, allow_new_signals=False, eligible_candidates=self.demo_eligible_candidates if self.demo_autotrade_enabled else None)
                                self.last_adaptive_result = adaptive
                                selected = adaptive.get('selected_candidate')
                                regime = adaptive.get('regime', 'UNKNOWN')
                                shown = selected or 'WAIT'
                                self.adaptive_status.set(f'{regime}  /  {shown}', adaptive.get('selection_reason', 'Нет подтверждённой статистики'))
                        except Exception as adaptive_error:
                            self.last_adaptive_result = None
                            self.adaptive_status.set('WAIT', f'Ошибка адаптивного контура: {adaptive_error}')
                        try:
                            result = analyze_candles(candles[-200:], payout=0.92)
                        except Exception as strategy_error:
                            result = {"signal": "WAIT", "reason": f"Ошибка ядра стратегии: {strategy_error}"}

                        signal = result.get("signal", "WAIT")
                        self.signal.setText(signal if signal in ("CALL", "PUT") else "ОЖИДАНИЕ")

                        signal_color = GREEN if signal == "CALL" else RED if signal == "PUT" else AMBER
                        self.signal.setStyleSheet(f"color:{signal_color}")

                        details = []
                        if "bullish_score" in result or "bearish_score" in result:
                            details.append(
                                f"Баллы CALL/PUT: {result.get('bullish_score', '—')}/{result.get('bearish_score', '—')}"
                            )

                        for key, label in (
                            ("rsi14", "RSI"),
                            ("ema8", "EMA 8"),
                            ("ema21", "EMA 21"),
                            ("ema50", "EMA 50"),
                            ("macd", "MACD"),
                            ("macd_histogram", "MACD Hist"),
                            ("adx14", "ADX"),
                        ):
                            if key in result:
                                details.append(f"{label}: {float(result[key]):.5f}")

                        reason = result.get("reason", "Нет пояснения от ядра.")
                        self.signal_note.setText(reason + ("  |  " + "  |  ".join(details) if details else ""))
                        self.m5.set(self.change(candles,5)); self.m15.set(self.change(candles,15)); self.m30.set(self.change(candles,30))
                        avg=sum(float(c['high']-c['low'])/0.0001 for c in recent)/len(recent); self.vol.set(f'{avg:.2f} пипса')
                    else:
                        self.trend.set('НЕ ДОСТУПНО','Окно данных не прошло проверку'); self.adaptive_status.set('WAIT','Адаптивный отбор заблокирован: данные не FRESH/непрерывны'); self.signal.setText('ОЖИДАНИЕ'); self.signal_note.setText('Текущий анализ заблокирован: данные устарели либо в последних 200 свечах есть разрывы.')
                        self.m5.set('Заблокировано'); self.m15.set('Заблокировано'); self.m30.set('Заблокировано'); self.vol.set('Заблокировано')
                else:
                    self.trend.set('НЕДОСТАТОЧНО ДАННЫХ',f'{len(candles)} из 200 свечей'); self.adaptive_status.set('WAIT','Нужно минимум 200 проверенных свечей'); self.signal.setText('ОЖИДАНИЕ')
            else:
                self.adaptive_status.set('WAIT','Нет корректных свечей'); self.price.set('—','Нет корректных свечей'); self.chart.set_candles([]); self.pro_chart.set_candles([]); self.trend.set('—','Нет данных'); self.last_candle.set('—'); self.gaps.set(len(rep['gaps']))
            if q['status']=='FRESH': self.market_badge.setText('● ДАННЫЕ СВЕЖИЕ'); self.market_badge.setStyleSheet(f'color:{GREEN}')
            elif q['status']=='STALE': self.market_badge.setText('● ДАННЫЕ УСТАРЕЛИ'); self.market_badge.setStyleSheet(f'color:{AMBER}')
            else: self.market_badge.setText('● ОШИБКА ДАННЫХ'); self.market_badge.setStyleSheet(f'color:{RED}')
            if self.observer.state() == QProcess.ProcessState.Running:
                self.start_btn.setText('?  ?????????? ????')

                if self.connection_status == "CONNECTED":
                    self.feed.set("??????????", "Pocket Option DEMO")
                elif self.connection_status == "DISCONNECTED":
                    self.feed.set(
                        "???????????????",
                        "????? ????????; ???????? ??????????????"
                    )
                else:
                    self.feed.set(
                        "???????????",
                        "???????? ????????????? DEMO"
                    )
            else:
                self.feed.set("??????????", "????? ?? ???????")
                self.start_btn.setText('?  ????????? ???? ??????')
        except Exception as e: self.log('Ошибка обновления панели: '+str(e))
    @staticmethod
    def change(candles,minutes):
        if len(candles)<=minutes: return 'Недостаточно данных'
        sample=candles[-(minutes+1):]
        if any((b['time']-a['time']).total_seconds()!=60 for a,b in zip(sample[:-1],sample[1:])): return 'Есть разрыв'
        return f'{(sample[-1]["close"]/sample[0]["close"]-1)*100:+.5f}%'
    def toggle_observer(self):
        if self.observer.state() == QProcess.ProcessState.Running:
            self.log("????????????? ???? ??????...")
            self.observer.terminate()
            if not self.observer.waitForFinished(5000):
                self.log("????????????? ????????? ???????.")
                self.observer.kill()
                self.observer.waitForFinished(3000)
            return

        if sys.platform != "win32":
            QMessageBox.warning(self, "Windows", "??????? ?????????????? ? Windows.")
            return

        token, accepted = QInputDialog.getText(
            self,
            "Pocket Option DEMO",
            "??????? Guest Token:",
            QLineEdit.EchoMode.Password
        )

        token = token.strip()
        if not accepted or not token:
            return

        if getattr(sys, "frozen", False):
            observer_exe = (
                Path(sys.executable).resolve().parent.parent
                / "HydraObserver"
                / "HydraObserver.exe"
            )
            if not observer_exe.exists():
                QMessageBox.critical(
                    self,
                    "??????? ?? ??????",
                    f"?? ?????? ???? ????????:\n{observer_exe}"
                )
                return
            program = str(observer_exe)
            arguments = []
        else:
            python = BASE / ".venv" / "Scripts" / "python.exe"
            if not python.exists():
                QMessageBox.critical(
                    self,
                    "Python ?? ??????",
                    f"?? ?????? ?????????????:\n{python}"
                )
                return
            program = str(python)
            arguments = ["-u", str(BASE / "guest_feed_reconnect.py")]

        self.live_price = None
        self.live_candle = None
        self.observer_stdout_buffer = ''

        env = QProcessEnvironment.systemEnvironment()
        env.insert("HYDRA_GUEST_TOKEN", token)
        self.observer.setProcessEnvironment(env)
        self.observer.setWorkingDirectory(str(BASE))
        self.connection_status = "CONNECTING"
        self.connection.setText("???????????: ???????????????...")
        self.observer.start(program, arguments)

        if not self.observer.waitForStarted(5000):
            self.connection_status = "STOPPED"
            QMessageBox.critical(
                self,
                "?????? ???????",
                "?? ??????? ????????? ???????. ??????? ??????."
            )
            return

        self.log("??????? ????? Guest Feed Collector.")
        self.connection.setText("???????????: ??????...")

    def process_live_candidate_signals(self, live_candle, tick_time, price):
        """Evaluate a completed M5 trigger with the first live M1 candle as entry reference."""
        if self.connection_status != "CONNECTED":
            return
        q = self.last_quality
        if not q or q.get("status") != "FRESH":
            return
        completed = q.get("candles", [])
        if len(completed) < 275:
            return
        try:
            last_time = completed[-1]["time"].astimezone(timezone.utc)
            live_time = live_candle["time"].astimezone(timezone.utc)
            tick_utc = tick_time.astimezone(timezone.utc)
            tick_age = (datetime.now(timezone.utc) - tick_utc).total_seconds()
            if (live_time - last_time) != timedelta(minutes=1) or tick_age < -2 or tick_age > 5:
                return
            if self.last_live_signal_minute == live_time:
                return
            self.last_live_signal_minute = live_time
            recent = completed[-200:]
            if any((b["time"] - a["time"]).total_seconds() != 60 for a, b in zip(recent[:-1], recent[1:])):
                return
            demo_completed = [
                DemoCandle(c["time"].astimezone(timezone.utc), float(c["open"]),
                           float(c["high"]), float(c["low"]), float(c["close"]))
                for c in completed
            ]
            live_demo = DemoCandle(live_time, float(live_candle["open"]),
                                   float(live_candle["high"]), float(live_candle["low"]),
                                   float(live_candle["close"]))
            adaptive = self.candidate_monitor.process(
                demo_completed + [live_demo], feed_ok=True,
                completed_candles=demo_completed, allow_new_signals=True,
                eligible_candidates=self.demo_eligible_candidates if self.demo_autotrade_enabled else None
            )
            self.last_adaptive_result = adaptive
            selected = adaptive.get("selected_candidate")
            regime = adaptive.get("regime", "UNKNOWN")
            self.adaptive_status.set(
                f"{regime}  /  {selected or 'WAIT'}",
                adaptive.get("selection_reason", "Нет подтверждённой статистики")
            )
            for signal in adaptive.get("new_signal_records", []):
                if selected != signal.get("candidate_id") or not self.demo_autotrade_enabled:
                    continue
                if self.execution_worker.state() != QProcess.ProcessState.Running:
                    continue
                payload = {
                    "candidate_id": signal["candidate_id"], "direction": signal["direction"],
                    "signal_time": signal["signal_time"], "entry_time": signal["entry_time"],
                    "expiry_minutes": int(signal["expiry_minutes"]),
                    "tick_time": tick_utc.isoformat(), "entry_price": float(price)
                }
                self.execution_worker.write((json.dumps(payload, separators=(",", ":")) + "\n").encode("utf-8"))
                self.execution_worker.waitForBytesWritten(1000)
                self.log(f"DEMO: сигнал {signal['candidate_id']} {signal['direction']} передан исполнителю; ожидается проверка брокера.")
        except Exception as exc:
            self.log("DEMO signal pipeline blocked: " + str(exc))

    def toggle_demo_autotrade(self):
        if self.demo_autotrade_enabled:
            self.demo_autotrade_enabled = False
            self.demo_btn.setText("DEMO АВТО: ОСТАНОВКА")
            if self.execution_worker.state() == QProcess.ProcessState.Running:
                self.execution_worker.write(b'{"command":"STOP"}\n')
                self.execution_worker.waitForBytesWritten(1000)
            return
        if self.execution_worker.state() == QProcess.ProcessState.Running:
            QMessageBox.information(self, "DEMO", "Исполнитель ещё завершает предыдущую операцию. Дождись статуса STOPPED.")
            return
        verification_path = BASE / "observer_data" / "demo_order_adapter_verified.json"
        try:
            verification = json.loads(verification_path.read_text(encoding="utf-8"))
        except Exception:
            verification = {}
        if verification.get("status") != "VERIFIED":
            QMessageBox.warning(self, "DEMO пока заблокирован", "Сначала выполни verify_demo_order.py: одна DEMO-сделка EURUSD на 1 единицу и 5 минут должна успешно закрыться. До этого автоисполнение заблокировано.")
            return
        if self.connection_status != "CONNECTED" or not self.last_quality or self.last_quality.get("status") != "FRESH":
            QMessageBox.warning(self, "DEMO заблокирован", "Сначала запусти сбор данных и дождись свежего непрерывного потока EURUSD.")
            return
        answer = QMessageBox.question(
            self, "Разрешить DEMO-автоисполнение?",
            "Разрешены только DEMO-сделки EURUSD без OTC. Ставка 1, без мартингейла. Минимальная фактическая выплата 92%, максимум одна позиция и дневной стоп 3 единицы. REAL запрещён. Продолжить?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )
        if answer != QMessageBox.StandardButton.Yes:
            return
        env = QProcessEnvironment.systemEnvironment()
        env.insert("HYDRA_DEMO_AUTOTRADE", "1")
        env.insert("HYDRA_ACCOUNT_MODE", "DEMO")
        env.insert("HYDRA_INSTRUMENT", "EURUSD")
        env.insert("HYDRA_ALLOW_OTC", "0")
        self.execution_worker.setProcessEnvironment(env)
        self.demo_eligible_candidates = set()
        if getattr(sys, "frozen", False):
            worker_exe = BASE / "HydraDemoExecution" / "HydraDemoExecution.exe"
            if not worker_exe.exists():
                QMessageBox.critical(self, "Исполнитель не найден", f"Не найден файл:\n{worker_exe}\nСначала собери HydraDemoExecution.spec.")
                return
            program, arguments = str(worker_exe), []
        else:
            python = BASE / ".venv" / "Scripts" / "python.exe"
            if not python.exists():
                python = Path(sys.executable)
            program, arguments = str(python), ["-u", str(BASE / "demo_execution_worker.py")]
        self.execution_worker.setWorkingDirectory(str(BASE))
        self.execution_worker.start(program, arguments)
        if not self.execution_worker.waitForStarted(5000):
            QMessageBox.critical(self, "DEMO", "Не удалось запустить DEMO-исполнитель. Сделки не отправляются.")
            return
        self.demo_autotrade_enabled = True
        self.demo_btn.setText("DEMO АВТО: ВКЛ")
        self.log("DEMO auto-execution enabled by explicit GUI confirmation. REAL/OTC remain blocked.")

    def read_execution_output(self):
        chunk = bytes(self.execution_worker.readAllStandardOutput()).decode("utf-8", "replace")
        self.execution_stdout_buffer += chunk
        while "\n" in self.execution_stdout_buffer:
            line, self.execution_stdout_buffer = self.execution_stdout_buffer.split("\n", 1)
            line = line.rstrip("\r")
            if not line:
                continue
            if line.startswith("HYDRA_EXECUTION|"):
                try:
                    payload = json.loads(line.split("|", 1)[1])
                    market = payload.get("market")
                    if isinstance(market, dict):
                        expiry_seconds = set(market.get("timeframes_seconds", []))
                        if market.get("status") == "ACTIVE":
                            expiry_by_candidate = {
                                "CAND-001": 300, "CAND-008": 1800,
                                "CAND-010": 3600, "CAND-012": 300, "CAND-014": 1800
                            }
                            self.demo_eligible_candidates = {
                                candidate_id for candidate_id, expiry in expiry_by_candidate.items()
                                if expiry in expiry_seconds
                            }
                        else:
                            self.demo_eligible_candidates = set()
                    self.log("DEMO исполнитель: " + str(payload))
                    if payload.get("status") == "STOPPED":
                        self.demo_autotrade_enabled = False
                        self.demo_btn.setText("DEMO АВТО: ВЫКЛ")
                except (ValueError, TypeError):
                    self.log("DEMO исполнитель: " + line)
            else:
                self.log("DEMO исполнитель: " + line)

    def read_execution_error(self):
        text = bytes(self.execution_worker.readAllStandardError()).decode("utf-8", "replace").strip()
        if text:
            self.log("DEMO исполнитель stderr: " + text[-1000:])

    def execution_finished(self, code, status):
        self.demo_autotrade_enabled = False
        self.demo_eligible_candidates = None
        self.demo_btn.setText("DEMO АВТО: ВЫКЛ")
        self.log(f"DEMO исполнитель завершён; code={code}, status={status}.")

    def handle_live_tick(self, payload):
        try:
            tick_time = datetime.fromisoformat(payload["time"])
            minute = datetime.fromisoformat(payload["minute"])

            price = float(payload["price"])
            candle = {
                "time": minute,
                "open": float(payload["open"]),
                "high": float(payload["high"]),
                "low": float(payload["low"]),
                "close": float(payload["close"]),
            }

            values = [
                price, candle["open"], candle["high"],
                candle["low"], candle["close"]
            ]

            if not all(0 < v < float("inf") for v in values):
                raise ValueError("Invalid live price")

            if (
                candle["low"] > min(candle["open"], candle["close"])
                or candle["high"] < max(candle["open"], candle["close"])
                or candle["low"] > candle["high"]
            ):
                raise ValueError("Invalid live OHLC")

            if tick_time.tzinfo is None or minute.tzinfo is None:
                raise ValueError("LIVE timestamps must include timezone")

            self.live_price = price
            self.live_candle = candle

            self.price.set(
                f"{price:.5f}",
                "??????? ???? ? Pocket Option DEMO"
            )

            if self.last_quality is not None:
                candles = self.last_quality["candles"]
                self.chart.set_candles(candles, candle)
                self.pro_chart.set_candles(candles, candle)
                self.process_live_candidate_signals(candle, tick_time, price)

        except (KeyError, TypeError, ValueError, OverflowError) as exc:
            self.log("???????????? LIVE-?????????: " + str(exc))

    def read_observer(self):
        chunk = bytes(
            self.observer.readAllStandardOutput()
        ).decode("utf-8", "replace")

        self.observer_stdout_buffer += chunk

        while "\n" in self.observer_stdout_buffer:
            line, self.observer_stdout_buffer = (
                self.observer_stdout_buffer.split("\n", 1)
            )
            line = line.rstrip("\r")

            if not line:
                continue

            if line.startswith("HYDRA_STATUS|"):
                try:
                    payload = json.loads(line[len("HYDRA_STATUS|"):])
                    if not isinstance(payload, dict):
                        raise ValueError("Status payload is not an object")
                    status = payload.get("status")
                    if status not in {"CONNECTING", "CONNECTED", "DISCONNECTED"}:
                        raise ValueError("Unknown connection status")

                    self.connection_status = status

                    if status == "CONNECTING":
                        self.connection.setText("???????????: ???????????????...")
                        self.log("DEMO: ??????????????? ??????????.")
                    elif status == "CONNECTED":
                        self.connection.setText("???????????: DEMO ???????")
                        self.log("DEMO: ?????????? ???????.")
                    elif status == "DISCONNECTED":
                        self.live_price = None
                        self.live_candle = None
                        self.connection.setText(
                            "???????????: ????????, ???????????????..."
                        )
                        self.log(
                            "DEMO: ????? ????????. "
                            + str(payload.get("details", ""))
                        )

                    self.refresh_data()
                except (json.JSONDecodeError, TypeError, ValueError) as exc:
                    self.log("???????????? HYDRA_STATUS: " + str(exc))
                continue

            if line.startswith("HYDRA_TICK|"):
                try:
                    payload = json.loads(line[len("HYDRA_TICK|"):])
                    self.handle_live_tick(payload)
                except json.JSONDecodeError as exc:
                    self.log("?????? LIVE JSON: " + str(exc))
                continue

            self.log(line)


    def read_observer_err(self):
        text = bytes(self.observer.readAllStandardError()).decode('utf-8', 'replace').strip()
        if text:
            self.log('???????: ' + text)

    def observer_finished(self, *args):
        if self.execution_worker.state() == QProcess.ProcessState.Running:
            self.demo_autotrade_enabled = False
            self.execution_worker.write(b'{"command":"STOP"}\n')
            self.execution_worker.waitForBytesWritten(1000)
        self.live_price = None
        self.live_candle = None
        self.connection_status = "STOPPED"
        self.observer_stdout_buffer = ''
        code = args[0] if args else '??????????'
        self.log(f'??????? ??????????. ???: {code}')
        self.connection.setText('Подключение: отключено')
        self.start_btn.setText('?  ????????? ???? ??????')
        self.refresh_data()

    def run_ai(self):
        if self.ai.state()==QProcess.ProcessState.Running: return
        q=self.last_quality
        if not q or q['status']!='FRESH' or len(q['candles'])<200:
            QMessageBox.warning(self,'Анализ недоступен','Для ИИ-анализа нужны свежие данные и минимум 200 корректных непрерывных свечей.'); return
        recent=q['candles'][-200:]
        if any((b['time']-a['time']).total_seconds()!=60 for a,b in zip(recent[:-1],recent[1:])):
            QMessageBox.warning(self,'Анализ заблокирован','В последних 200 свечах есть временной разрыв.'); return
        if getattr(sys, "frozen", False):
            analyzer_exe = BASE / "HydraAnalyzer" / "HydraAnalyzer.exe"
            if not analyzer_exe.exists():
                QMessageBox.critical(
                    self,
                    "Analyzer not found",
                    f"File not found:\n{analyzer_exe}"
                )
                return
            program = str(analyzer_exe)
            arguments = []
        else:
            python = BASE / ".venv" / "Scripts" / "python.exe"
            if not python.exists():
                python = Path(sys.executable)
            program = str(python)
            arguments = ["-u", str(BASE / "hydra_ai_analyzer.py")]

        self.ai_output.append('\nStarting local Qwen 2.5 7B analysis...')
        self.ai.start(program, arguments)
        self.analyze_btn.setEnabled(False)
        self.ai_status.set("RUNNING", "Waiting for Ollama response")
    def read_ai(self):
        text=bytes(self.ai.readAllStandardOutput()).decode('utf-8','replace')
        if text: self.ai_output.append(text); self.log('ИИ-анализ: получен вывод.')
    def read_ai_err(self):
        text=bytes(self.ai.readAllStandardError()).decode('utf-8','replace')
        if text: self.ai_output.append(text); self.log('ИИ stderr: '+text[-500:])
    def ai_finished(self,code,status):
        self.analyze_btn.setEnabled(True)
        if code==0: self.ai_status.set('ЗАВЕРШЁН','Смотри вкладку «ИИ-анализ»'); self.log('ИИ-анализ завершён успешно.')
        else: self.ai_status.set('ОШИБКА','Проверь Ollama и журнал'); self.log(f'ИИ-анализ завершился с кодом {code}.')
        if AI_LOG.exists():
            try: self.ai_output.setPlainText(AI_LOG.read_text(encoding='utf-8',errors='replace')[-20000:])
            except Exception: pass
    def check_ollama(self):
        try:
            with urllib.request.urlopen('http://localhost:11434/api/tags',timeout=2) as r: data=json.loads(r.read())
            models=[m.get('name','') for m in data.get('models',[])]
            ok=any(x.startswith('qwen2.5:7b') for x in models)
            self.ai_status.set('ГОТОВ' if ok else 'OLLAMA ЕСТЬ','Qwen 2.5 7B найден' if ok else 'Модель qwen2.5:7b не найдена')
        except Exception: self.ai_status.set('НЕ ДОСТУПЕН','Запусти Ollama и проверь Qwen 2.5 7B')
    def closeEvent(self,event):
        if self.execution_worker.state() == QProcess.ProcessState.Running:
            self.demo_autotrade_enabled = False
            self.execution_worker.write(b'{"command":"STOP"}\n')
            self.execution_worker.waitForBytesWritten(1000)
            if not self.execution_worker.waitForFinished(5000):
                QMessageBox.warning(self, "DEMO-сделка ещё выполняется", "Исполнитель не завершился за 5 секунд. Дождись закрытия текущей позиции и затем закрой HydraAI. Новые сигналы больше не отправляются.")
                event.ignore()
                return
        if self.observer.state()==QProcess.ProcessState.Running:
            self.observer.terminate(); self.observer.waitForFinished(4000)
        event.accept()

def main():
    app = QApplication(sys.argv)
    app.setStyle('Fusion')
    app.setWindowIcon(QIcon(str(Path(__file__).resolve().parent / "logo.ico")))

    w = HydraWindow()
    w.setWindowIcon(QIcon(str(Path(__file__).resolve().parent / "logo.ico")))
    w.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()