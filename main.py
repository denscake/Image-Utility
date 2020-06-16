import os, sys, shutil, time
from PIL import Image, ImageStat
from PyQt5.QtWidgets import QApplication, QMainWindow, QAction
from thing import Ui_MainWindow
from notathing import Ui_MainWindow as UI_HelperWindow
from realthing import Ui_MainWindow as UI_SorterWindow
from finalthing import Ui_MainWindow as UI_ExternalWindow
from PyQt5.QtWidgets import QFileDialog, QMessageBox
from time import gmtime, strftime
from PyQt5 import QtCore, QtWidgets
from PyQt5.QtGui import QPixmap
from PyQt5.QtCore import Qt
from functools import partial

STOP = False
EXTERNAL_WINDOW_PAUSE = False
CONTAINER_BOX = []  # тут мы будем хранить контейнеры, чтобы далеко не бегать поставим его возле входа
EKATERINBURG_MOSKVA = ""

EXT_KEYS = []
EXT_KEYS_NAMES = []
EXT_ITEMS = []
EXT_WORKING_DIRECTORY = ""


class ImageContainer():  # будем его использовать для хранения тучи исформации, а то списки перестали быть удобными
    fullPath = ""
    directory = ""
    fileName = ""
    fileHash = 0
    area = 0
    delete = False
    abscent = False
    save = False
    w = 0
    h = 0
    pass


class MainWindow(QMainWindow, Ui_MainWindow):
    switch_window = QtCore.pyqtSignal()

    workingDirectory = "C:/"

    def __init__(self):
        super().__init__()
        self.setupUi(self)
        self.directory.setText(self.workingDirectory)
        self.BrowseButton.clicked.connect(self.run)
        self.RunButton.clicked.connect(self.start_processing)
        self.menu_action = QAction('Открыть', self)
        self.menu_action.setData('option1')
        self.menu_action.triggered.connect(self.open_sorter)

        self.menu.addAction(self.menu_action)

    def run(self):  # узнаем у пользователя гд будем работать
        directory = QFileDialog.getExistingDirectory(None, 'Выберите папку с изображениями:', 'C:/',
                                                     QFileDialog.ShowDirsOnly)
        if directory:
            self.workingDirectory = directory
        if os.path.isdir(self.workingDirectory):
            self.directory.setText(self.workingDirectory)
        else:
            QMessageBox.about(self, "Ошибка", "Путь недоступен.")

    def open_sorter(self):  # открываем настройку помощника сортировки
        self.switch_window.emit()
        self.close()

    def stop(self):  # перерыв
        global STOP
        STOP = True
        self.RunButton.clicked.disconnect(self.stop)
        self.RunButton.setText("Продолжить")
        self.RunButton.clicked.connect(self.resume)
        while STOP:
            time.sleep(0.01)
            QApplication.processEvents()

    def resume(self):  # продолжаем работать
        global STOP
        STOP = False
        self.RunButton.clicked.disconnect(self.resume)
        self.RunButton.setText("Остановить")
        self.RunButton.clicked.connect(self.stop)

    def start_processing(self):  # все еще только начинается
        self.action.setText("Начало")
        self.BrowseButton.setEnabled(False)
        self.RunButton.clicked.disconnect(self.start_processing)
        self.RunButton.setText("Остановить")
        self.RunButton.clicked.connect(self.stop)
        self.directory.setEnabled(False)
        self.label.setEnabled(False)
        self.label_2.setEnabled(False)
        self.menu.setEnabled(False)
        time.sleep(0.5)
        self.process_dups(self.find_dup(self.workingDirectory))
        self.finish()

    def finish(self):  # когда все закончилось
        self.action.setText("Готово")
        self.BrowseButton.setEnabled(True)
        self.RunButton.clicked.disconnect(self.stop)
        self.RunButton.setText("Найти дубликаты")
        self.RunButton.clicked.connect(self.start_processing)
        self.directory.setEnabled(True)
        self.label.setEnabled(True)
        self.label_2.setEnabled(True)
        self.menu.setEnabled(True)

    def find_dup(self, parent_folder):
        # Ищем дубликаты и выдаем в формате hash:{Files}
        counter = 0
        duplicates = {}

        fileList = [f for f in os.listdir(parent_folder) if os.path.isfile(os.path.join(parent_folder, f))]

        temp_paths = []
        file_count = len(fileList)
        for filename in fileList:
            counter += 1
            self.action.setText(f"Сканируем файл {counter} из {file_count}")
            self.progressBar.setValue(int((counter * 1.0 / file_count) * 100))
            QApplication.processEvents()
            # Собираем из частей полный путь к файлу
            path = os.path.join(parent_folder, filename)
            temp_paths.append(path)
            # Считаем хэш
        res = []
        self.action.setText(f"Хэшируем изображения")
        QApplication.processEvents()
        file_count = len(temp_paths)
        counter = 0
        for i in temp_paths:  # выводим на экран всякое
            counter += 1
            res.append(self.proc_img(i))
            self.action.setText(f"Хешируем изображение {counter} из {file_count}")
            self.progressBar.setValue(int((counter * 1.0 / file_count) * 100))
            QApplication.processEvents()
        for i in res:
            if i[0] in duplicates:
                duplicates[i[0]].append(i[1])
            else:
                duplicates[i[0]] = [i[1]]

        return duplicates

    def proc_img(self, path):
        try:
            img = Image.open(path).resize((8, 8), Image.LANCZOS).convert(mode="L")
            mean = ImageStat.Stat(img).mean[0]
            file_hash = sum((1 if p > mean else 0) << i for i, p in enumerate(img.getdata()))
        except Exception:
            file_hash = 0
            pass
        return [file_hash, path]

    def process_dups(self, dict1):
        global CONTAINER_BOX
        global EXTERNAL_WINDOW_PAUSE
        global EKATERINBURG_MOSKVA
        EKATERINBURG_MOSKVA = []
        self.flush_container()
        self.action.setText(f"Начинаем сравнивать изображения")
        QApplication.processEvents()

        very_long_list = []

        directory = ""

        results = list(filter(lambda x: len(x) > 1, dict1.values()))  # перобразуем в список
        file_count = len(results)
        counter = 0
        isolated = 0  # это у нас список со всеми файлами которые почти дубликаты
        deletion_list = []  # список чего удалить
        if len(results) > 0:  # проверка на пустой список

            for result in results:  # проходим по дубликатам
                counter += 1
                self.action.setText(f"Рассматриваем группу {counter} из {file_count}")
                self.progressBar.setValue(int((counter * 1.0 / file_count) * 100))
                QApplication.processEvents()

                literally_pile_of_garbage = []

                for subresult in result:  # рассматриваем отдельный элемент
                    head, tail = os.path.split(subresult)
                    subject = ImageContainer()
                    subject.directory = head
                    subject.fileName = tail
                    subject.fullPath = subresult
                    CONTAINER_BOX.append(subject)

                    literally_pile_of_garbage.append(CONTAINER_BOX[-1])

                    directory = head

                group = []
                for item in literally_pile_of_garbage:  # получаем всякие параметры картинки
                    img = Image.open(item.fullPath)
                    width, height = img.size
                    area = width * height
                    img = img.resize((12, 12), Image.LANCZOS).convert(mode="L")
                    mean = ImageStat.Stat(img).mean[0]
                    image_hash = sum((1 if p > mean else 0) << T for T, p in enumerate(img.getdata()))
                    item.fileHash = mean
                    item.area = area
                    item.w = width
                    item.h = height

                    group.append(item)

                sorted_groups = sorted(group, key=lambda x: x.area, reverse=True)  # сортируем по убыванию разрешения

                group_hashes = []  # какие хеши вообще у нас есть
                for item in sorted_groups:
                    group_hashes.append(item.fileHash)

                diff_groups = []  # какие группы бывают
                for item in sorted_groups:
                    if not (item.fileHash in diff_groups):
                        diff_groups.append(item.fileHash)

                for group in diff_groups:  # считаем сколько раз каждый хеш в группе встретился
                    diff_groups[diff_groups.index(group)] = [group, group_hashes.count(group)]

                diff_groups = sorted(diff_groups, key=lambda x: x[1],
                                     reverse=True)  # какие чаще встречаются, те и главные

                main_hash = diff_groups[0][0]
                main_items = []
                isolated_items = []
                for item in sorted_groups:
                    if item.fileHash == main_hash:
                        main_items.append(item)
                    else:
                        isolated_items.append(item)
                # так мы получили те элементы которые мы будем сравнивать и спорные элементы в отдельном списке

                final_distribution = [main_items[0], main_items[1:], isolated_items]
                # мы получили список [ оставить, удалить, под вопросом]
                very_long_list.append(final_distribution)

            # собираем список чего бы удалить

            if very_long_list:
                for item in very_long_list:
                    for item_1 in item[1]:
                        item_1.delete = True

            # это у нас список со всеми файлами которые почти дубликаты
            if very_long_list:
                for item in very_long_list:
                    for _ in item[2]:
                        isolated += 1

                        # говорим что нашли
        self.delete_items_count = 0
        for item in CONTAINER_BOX:
            if item.delete:
                self.delete_items_count += 1
        if self.delete_items_count:
            qm = QMessageBox
            ret = qm.information(self, 'Отчет', f"Найдено дубликатов: {self.delete_items_count}"
                                                "\n Удалить убликаты?",
                                 qm.Yes | qm.No)
            if ret == qm.No:
                for item in CONTAINER_BOX:
                    item.delete = False
                self.delete_items_count = 0
        else:
            qm = QMessageBox
            _ = qm.information(self, 'Отчет', "Дубликатов не найдено")

        if isolated:  # спрашиваем хочет ли пользователь удалить все или отсортировать вручную

            qm = QMessageBox
            ret = qm.question(self, 'Нам требуется ваше решение',
                              f"Найдены фото ({isolated}), которые могут не являться дубликатами. "
                              "\n Хотите выбрать какие из них сохранить?",
                              qm.Yes | qm.SaveAll | qm.Discard)
            if ret == qm.Yes:  # вызываем помощник выбора
                EKATERINBURG_MOSKVA = very_long_list
                self.hide()
                EXTERNAL_WINDOW_PAUSE = True
                Hub.show_helper(Hub)

            # здесь мог быть код обработки SaveAll, но чтобы их не удалить не нужно ничего делать

            if ret == qm.Discard:
                temp_list = []
                for item in very_long_list:  # преобразуем параллельный список в последовательный
                    if item[2]:
                        for i in item[2]:
                            temp_list.append(i)
                for item in temp_list:  # удаляем
                    item.delete = True
                    self.delete_items_count += 1

        while EXTERNAL_WINDOW_PAUSE:  # тормозим выполнение, так как другое окно не завершило свое действие
            time.sleep(0.01)
            QApplication.processEvents()


        time_stamp = strftime("%Y_%m_%d_%H_%M", gmtime())  # удаляем потихонечку
        if self.delete_items_count:
            delete_folder = directory + "/TO_BE_DELETED " + time_stamp
            if not (os.path.isdir(delete_folder)):
                os.mkdir(delete_folder)

            for item in CONTAINER_BOX:  # прямо потихонечку, так чтобы ничего не исчезло
                if item.delete:
                    try:  # на всякий слоучай
                        shutil.move(item.fullPath, delete_folder)
                    except:
                        pass

                # move_to = nfldr

    def flush_container(self):  # очистка контейнера, ну оч надо выкинуть из него хлам
        global CONTAINER_BOX
        CONTAINER_BOX = []

    def woosh(self):  # по факту просто открыть окно
        global EXTERNAL_WINDOW_PAUSE
        self.show()
        EXTERNAL_WINDOW_PAUSE = False

    def reappear(self):
        temp_list = []
        for item in EKATERINBURG_MOSKVA:  # преобразуем параллельный список в последовательный
            if item[2]:
                temp_list.append(item[0])
                for i in item[2]:
                    temp_list.append(i)
        for item in temp_list:  # собсна те которые не сохраняем, удаляем
            if not item.save:
                item.delete = True
                self.delete_items_count += 1
        self.woosh()  # опа, фокус, окно появилось


class SorterWindow(QMainWindow, UI_SorterWindow):
    switch_window = QtCore.pyqtSignal()
    items = []
    working_directory = "C:/"

    def back_to_the_main(self):  # возвращаемся обратно на главное окно
        # #вообще работать с таким количеством окон неудобно без изначально нормального плана
        self.switch_window.emit()
        self.close()

    def __init__(self):
        self.items = []
        super().__init__()
        self.setupUi(self)
        self.Return.clicked.connect(self.back_to_the_main)
        self.Pathedit.clicked.connect(self.change_path)
        self.Next.clicked.connect(self.next)
        self.key_list = [Qt.Key_1, Qt.Key_2, Qt.Key_3, Qt.Key_4, Qt.Key_5, Qt.Key_6, Qt.Key_7, Qt.Key_8, Qt.Key_9,
                         Qt.Key_0]  # планировалось больше, но остальные не работают
        self.key_name_list = [1, 2, 3, 4, 5, 6, 7, 8, 9, 0]
        self.Pathline.setText(self.working_directory)
        for i in range(len(self.key_list)):  # рисуем строчки с выбором путей и тд
            self.ItemLayout = QtWidgets.QHBoxLayout()
            self.ItemLayout.setObjectName(f"ItemLayout{i}")
            self.EnableCheck = QtWidgets.QCheckBox(self.scrollAreaWidgetContents)
            self.EnableCheck.setObjectName(f"EnableCheck{i}")
            self.ItemLayout.addWidget(self.EnableCheck)
            self.line = QtWidgets.QFrame(self.scrollAreaWidgetContents)
            self.line.setFrameShape(QtWidgets.QFrame.VLine)
            self.line.setFrameShadow(QtWidgets.QFrame.Sunken)
            self.line.setObjectName(f"line{i}")
            self.ItemLayout.addWidget(self.line)
            self.Keyname = QtWidgets.QLabel(self.scrollAreaWidgetContents)
            self.Keyname.setObjectName(f"Keyname{i}")
            self.ItemLayout.addWidget(self.Keyname)
            self.KeyPath = QtWidgets.QLineEdit(self.scrollAreaWidgetContents)
            self.KeyPath.setReadOnly(True)
            self.KeyPath.setText("C:/")
            self.KeyPath.setObjectName(f"KeyPath{i}")
            self.ItemLayout.addWidget(self.KeyPath)
            self.KeyEdit = QtWidgets.QPushButton(self.scrollAreaWidgetContents)
            self.KeyEdit.setObjectName(f"KeyEdit{i}")
            self.ItemLayout.addWidget(self.KeyEdit)
            self.verticalLayout_3.addLayout(self.ItemLayout)
            self.EnableCheck.setText("Включить")
            self.Keyname.setText(f"Кнопка: {self.key_name_list[i]}")
            self.KeyEdit.setText("Выбрать путь")
            self.items.append([self.EnableCheck, self.KeyPath, "C:\\oops", False])
            # чекбокс, строчка, путь, был ли выбран элемент

            arg = partial(self.indexed_browser, i)
            self.KeyEdit.clicked.connect(arg)

        spacerItem = QtWidgets.QSpacerItem(20, 40, QtWidgets.QSizePolicy.Minimum, QtWidgets.QSizePolicy.Expanding)
        self.verticalLayout_3.addItem(spacerItem)

    def change_path(self):
        directory = QFileDialog.getExistingDirectory(None, 'Выберите папку с изображениями:',
                                                     'C:/',
                                                     QFileDialog.ShowDirsOnly)
        if directory:
            self.working_directory = directory
        if os.path.isdir(self.working_directory):
            self.Pathline.setText(self.working_directory)  # не сильно нужная проверка на ошибки
        else:
            self.working_directory = "C:\\oops"
            QMessageBox.about(self, "Ошибка", "Путь недоступен.")

    def indexed_browser(self, index):

        directory = QFileDialog.getExistingDirectory(None, 'Выберите папку в которую будут перемещены изображения:',
                                                     'C:/',
                                                     QFileDialog.ShowDirsOnly)
        if directory:
            self.items[index][2] = directory
        if os.path.isdir(self.items[index][2]):
            self.items[index][1].setText(self.items[index][2])  # так же не сильно нужная проверка на ошибки
        else:
            self.items[index][2] = "C:\\oops"
            QMessageBox.about(self, "Ошибка", "Путь недоступен.")

    def next(self):
        global EXTERNAL_WINDOW_PAUSE
        for item in self.items:
            if item[0].checkState() == 2:
                item[3] = True
        global EXT_ITEMS
        global EXT_KEYS
        global EXT_KEYS_NAMES
        global EXT_WORKING_DIRECTORY  # кидаем данные прямо вверх, потом поймаем
        EXT_ITEMS = self.items
        EXT_KEYS = self.key_list
        EXT_KEYS_NAMES = self.key_name_list
        EXT_WORKING_DIRECTORY = self.working_directory
        Hub.show_external(Hub)
        self.hide()
        EXTERNAL_WINDOW_PAUSE = True
        while EXTERNAL_WINDOW_PAUSE:  # тормозим выполнение, так как другое окно не завершило свое действие
            time.sleep(0.01)
            QApplication.processEvents()
        self.switch_window.emit()


class HelperWindow(QMainWindow, UI_HelperWindow):
    global EKATERINBURG_MOSKVA
    # время преобразовывать одни данные в другие

    switch_window = QtCore.pyqtSignal()

    checklink = []
    group_item = []
    group_index = 0

    def __init__(self):
        super().__init__()
        self.setupUi(self)
        self.forButton.clicked.connect(self.nextPage)
        self.revButton.clicked.connect(self.prevPage)
        self.endButton.clicked.connect(self.exit)
        # инициализация интерфейса и преобразование одного списка в другой, более удобный
        self.group_item = []
        for item in EKATERINBURG_MOSKVA:
            if item[2]:
                part1 = [item[0]]
                part2 = []
                for i in item[2]:
                    part2.append(i)
                self.group_item.append(part1 + part2)

        self.doButtonStuff()

    def drawStuff(self):
        self.checklink = []  # сохраняем всё что нам надо сюда и носим с собой
        for i in range(len(self.group_item[self.group_index])):  # добавляем элементы в грид
            item = self.group_item[self.group_index]
            self.ItemFrame = QtWidgets.QFrame(self.scrollAreaWidgetContents)
            self.ItemFrame.setMinimumSize(QtCore.QSize(250, 350))
            sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Expanding)
            sizePolicy.setHorizontalStretch(0)
            sizePolicy.setVerticalStretch(0)
            sizePolicy.setHeightForWidth(self.ItemFrame.sizePolicy().hasHeightForWidth())
            self.ItemFrame.setSizePolicy(sizePolicy)
            self.ItemFrame.setFrameShape(QtWidgets.QFrame.StyledPanel)
            self.ItemFrame.setFrameShadow(QtWidgets.QFrame.Plain)
            self.ItemFrame.setLineWidth(1)
            self.ItemFrame.setObjectName(f"ItemFrame{i}")
            self.ItemFrame.setAutoFillBackground(True)
            self.verticalLayout_2 = QtWidgets.QVBoxLayout(self.ItemFrame)
            self.verticalLayout_2.setObjectName(f"verticalLayout_2{i}")
            self.NameLabel = QtWidgets.QLabel(self.ItemFrame)
            self.NameLabel.setObjectName(f"NameLabel{i}")
            self.NameLabel.setText(item[i].fileName)  ##################
            self.verticalLayout_2.addWidget(self.NameLabel)
            self.ResLabel = QtWidgets.QLabel(self.ItemFrame)
            self.ResLabel.setObjectName(f"ResLabel{i}")
            self.ResLabel.setText(f"{item[i].w}x{item[i].h} {item[i].area / 1000000.0}MP")  ###############
            self.verticalLayout_2.addWidget(self.ResLabel)
            self.Itemcheck = QtWidgets.QCheckBox(self.ItemFrame)
            self.Itemcheck.setObjectName(f"Itemcheck{i}")
            self.Itemcheck.setText("Сохранить")
            self.verticalLayout_2.addWidget(self.Itemcheck)
            self.Image = QtWidgets.QLabel(self.ItemFrame)
            self.Image.setMinimumSize(QtCore.QSize(230, 268))
            self.Image.setSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Expanding)
            self.pixmap = QPixmap(item[i].fullPath)  #######
            self.Image.setPixmap(self.pixmap)
            QApplication.processEvents()
            self.Image.setObjectName(f"Image{i}")
            self.checklink.append([self.Itemcheck, self.Image, self.pixmap, item[i]])
            self.verticalLayout_2.addWidget(self.Image)
            self.gridLayout.addWidget(self.ItemFrame, (i / 3), (i % 3), 1, 1)
            self.Itemcheck.setChecked(item[i].save)  #

        for item in self.checklink:
            item[1].setPixmap(item[2].scaled(item[1].size(), QtCore.Qt.KeepAspectRatio))

    def nextPage(self):  # шагаем на страничку врепед
        if self.group_index < len(self.group_item) - 1:
            self.group_index += 1
        self.doButtonStuff()

    def prevPage(self):  # идем на страничку назад
        if self.group_index > 0:
            self.clearLayout()
            self.group_index -= 1
        self.doButtonStuff()

    def doButtonStuff(self, i=1):

        for item in self.checklink:  # сохраняем состояние перед перелистыванием
            QApplication.processEvents()
            state = item[0].checkState()
            if state == 2:
                item[3].save = True
            else:
                item[3].save = False
                # и блин работает же

        self.clearLayout()  # очищаем грид
        if i:
            self.drawStuff()  # добавляем на него элементы

        if not (self.group_index < len(self.group_item) - 1):  # уже делал код меньше, но выходит непонятно
            self.forButton.setEnabled(False)  # вобщем мы тут скрываем кнопочки
        else:
            self.forButton.setEnabled(True)
        if not (self.group_index > 0):
            self.revButton.setEnabled(False)
        else:
            self.revButton.setEnabled(True)

        self.PagLabel.setText(f"{self.group_index + 1}/{len(self.group_item)}")  # обновляем надпись
        self.refreshImages(1)  # фиксим размер изображения

    def clearLayout(self):  # удаляем более не нужные элементы, чтобы нарисовать новые
        layout = self.gridLayout
        while layout.count() > 0:
            item = layout.takeAt(0)

            if not item:
                continue
            w = item.widget()
            if w:
                w.deleteLater()

    def resizeEvent(self, event):  # поддерживаем картинки в хорошем состоянии
        self.refreshImages()

    def keyPressEvent(self, event):  # обрабатываем нажатия кнопок
        if event.key() == Qt.Key_1:  # кстати стрелочки не работают, окно их перехватывает раньше
            self.prevPage()
        elif event.key() == Qt.Key_2:
            self.nextPage()

    def refreshImages(self, res=0):
        # костыль, но другого решения я не нашел
        if res:
            for item in self.checklink:
                item[1].setPixmap(item[2].scaled(res, res, QtCore.Qt.KeepAspectRatio))

            QApplication.processEvents()  # ресайзится сам грид, и это помогает с размерами

        for item in self.checklink:
            item[1].setPixmap(item[2].scaled(item[1].size(), QtCore.Qt.KeepAspectRatio))

    def exit(self):
        self.doButtonStuff()  # чисто чтобы сохранить состояние
        global MAIN_OBJECT
        qm = QMessageBox
        ret = qm.question(self, 'Подождите, не уходите',
                          "Все не отмеченные изображения будут удалены!\nПродолжить?",
                          qm.Yes | qm.SaveAll | qm.Cancel)
        if ret == qm.Yes:
            MAIN_OBJECT.reappear()  # а вы знаете что такое костыли?
            self.close()  # ну как минимум оно не крашится
        if ret == qm.SaveAll:
            MAIN_OBJECT.woosh()
            self.close()

        # уже неплохо


class ExtWindow(QMainWindow, UI_ExternalWindow):
    index = 0

    def __init__(self):
        global EXT_ITEMS
        global EXT_KEYS
        global EXT_KEYS_NAMES
        global EXT_WORKING_DIRECTORY
        super().__init__()
        self.setupUi(self)
        self.done.clicked.connect(self.exit)

        first = True

        spacerItem = QtWidgets.QSpacerItem(40, 20, QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Minimum)
        self.horizontalLayout_2.addItem(spacerItem)  # спейсер в начале

        self.folder_list = []

        for i in range(len(EXT_ITEMS)):
            item = EXT_ITEMS[i]
            self.folder_list.append([])  # сюда будем файлы раскидывать
            if item[3]:  # кнопочки раскидываем
                if not first:
                    self.line_2 = QtWidgets.QFrame(self.centralwidget)
                    self.line_2.setFrameShape(QtWidgets.QFrame.VLine)
                    self.line_2.setFrameShadow(QtWidgets.QFrame.Sunken)
                    self.line_2.setObjectName("line_2")
                    self.horizontalLayout_2.addWidget(self.line_2)  # линии разделяющие
                first = False
                self.keylabel = QtWidgets.QLabel(self.centralwidget)
                self.keylabel.setObjectName("keylabel")
                self.horizontalLayout_2.addWidget(self.keylabel)
                filename = item[2].split(sep="/")

                self.keylabel.setText(f"Кнопка {EXT_KEYS_NAMES[i]} : [{filename[-1]}]")
        spacerItem = QtWidgets.QSpacerItem(40, 20, QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Minimum)
        self.horizontalLayout_2.addItem(spacerItem)  # спейсер в конце

        self.fileList = [f for f in os.listdir(EXT_WORKING_DIRECTORY)
                         if os.path.isfile(os.path.join(EXT_WORKING_DIRECTORY, f))]
        self.draw_stuff()

    def next(self):  # перемещаемся к следующему элементу
        if self.index < len(self.fileList) - 1:
            self.index += 1
            self.draw_stuff()
        else:
            self.exit()

    def draw_stuff(self):
        self.ItemName.setText(self.fileList[self.index])
        filepath = EXT_WORKING_DIRECTORY + "/" + self.fileList[self.index]
        success = False  # еще понадобится, но обращайте внимание, я знаю что делаю..
        try:
            self.pixmap = QPixmap(filepath)  # ..в пропасть прыгаю
            self.Image.setPixmap(self.pixmap)
            success = True  # парашют сработал
        except:
            pass
        if not success:  # если парашют не сработал, включаем антигравитацию
            self.next()

        self.resize_image()

        QApplication.processEvents()

    def resizeEvent(self, event):
        self.resize_image()

    def resize_image(self):
        self.Image.setPixmap(self.pixmap.scaled(self.Image.size(), QtCore.Qt.KeepAspectRatio))
        pass

    def keyPressEvent(self, event):
        global EXT_ITEMS
        for i in range(len(EXT_KEYS)):
            item = EXT_ITEMS[i]
            if item[3]:
                if event.key() == EXT_KEYS[i]:
                    filepath = EXT_WORKING_DIRECTORY + "/" + self.fileList[self.index]
                    self.folder_list[i].append(filepath)
                    self.next()
                    continue

    def exit(self):
        global EXT_ITEMS
        for i in range(len(self.folder_list)):  # перемещаем фотки
            items = self.folder_list[i]
            if items:
                for item in items:
                    try:
                        shutil.move(item, EXT_ITEMS[i][2])  # не работает если файл в папке есть
                    except:
                        pass

        global EXTERNAL_WINDOW_PAUSE  # возвращаем старое окошко
        EXTERNAL_WINDOW_PAUSE = False
        self.close()


MAIN_OBJECT = ""


class Hub():

    def __init__(self):
        pass

    def show_main(self):
        global MAIN_OBJECT
        self.main = MainWindow()
        MAIN_OBJECT = self.main
        self.main.switch_window.connect(self.show_sorter)
        self.main.show()

    def show_sorter(self):  # вызов окна настройки помощника сортировки
        self.sort = SorterWindow()
        self.sort.switch_window.connect(self.show_main)
        self.sort.setWindowFlags(Qt.CustomizeWindowHint | Qt.WindowTitleHint | Qt.WindowMinMaxButtonsHint)
        self.sort.show()

    def show_helper(self):
        self.help = HelperWindow()
        self.help.setWindowFlags(Qt.CustomizeWindowHint | Qt.WindowTitleHint | Qt.WindowMinMaxButtonsHint)
        self.help.switch_window.connect(self.show_main)
        self.help.show()
        self.help.showMaximized()

    def show_external(self):  # вызов окна помощника сортировки
        self.ext = ExtWindow()
        self.ext.setWindowFlags(Qt.CustomizeWindowHint | Qt.WindowTitleHint | Qt.WindowMinMaxButtonsHint)
        self.ext.show()
        self.ext.showMaximized()


app = QApplication(sys.argv)  # а вот тут то все и началось
application = Hub()
application.show_main()
sys.exit(app.exec_())
