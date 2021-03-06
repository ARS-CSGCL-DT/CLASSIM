from PyQt5 import QtSql, QtCore, QtGui
from PyQt5.QtWidgets import QWidget, QTabWidget, QDialog, QLabel, QHBoxLayout, QTableWidget, QTableWidgetItem, QComboBox, QVBoxLayout, \
                            QPushButton, QSpacerItem, QSizePolicy, QMenu, QHeaderView
from PyQt5.QtCore import pyqtSlot
from CustomTool.custom1 import *
from CustomTool.UI import *
from DatabaseSys.Databasesupport import *
from Models.cropdata import *
from TabbedDialog.tableWithSignalSlot import *
from functools import partial
import requests
import json
import xmltodict
import pandas as pd

'''
Contains 2 classes.
1). Class ItemWordWrap is to assist the text wrap features. You will find this class at the top of all the 
    tab classes. In future,we can centralize it. Lower priority.

2). Class Soil_Widget is derived from Qwidget. It is initialed and called by Tabs.py -> class Tabs_Widget. 
    It handles all the features of SOIL Tab on the interface.
    It has signal slot mechanism. It does interact with the DatabaseSys\Databasesupport.py for all the 
    databases related task.
    Pretty generic and self explanotory methods. 
    Refer baseline classes at http://pyqt.sourceforge.net/Docs/PyQt5/QtWidgets.html#PyQt5-QtWidgets

    Tab screen is divided into 2 main panels.
    Left panel does the heavy lifting and interacts with user. 
    Right panel is mainly for frequently asked questions (FAQ) stored in sqlite table "Faq".
'''

class ItemWordWrap(QtWidgets.QStyledItemDelegate):
    def __init__(self, parent=None):
        QtWidgets.QStyledItemDelegate.__init__(self, parent)
        self.parent = parent


    def paint(self, painter, option, index):
        text = index.model().data(index) 
        #print("text=", text)
        
        document = QtGui.QTextDocument() 
        document.setHtml(text) 
        
        document.setTextWidth(option.rect.width())  #keeps text from spilling over into adjacent rect
        index.model().setData(index, option.rect.width(), QtCore.Qt.UserRole+1)
        painter.setPen(QtGui.QPen(Qt.blue))        
        painter.save() 
        painter.translate(option.rect.x(), option.rect.y())         
        document.drawContents(painter)  #draw the document with the painter        
        painter.restore() 


    def sizeHint(self, option, index):
        #Size should depend on number of lines wrapped
        text = index.model().data(index)
        document = QtGui.QTextDocument()
        document.setHtml(text) 
        width = index.model().data(index, QtCore.Qt.UserRole+1)
        if not width:
            width = 20
        document.setTextWidth(width) 
        return QtCore.QSize(document.idealWidth() + 10,  document.size().height())


#this is widget of type 1. It would be added to as a tab
class Soil_Widget(QWidget):
    def __init__(self):
        super(Soil_Widget,self).__init__()
        self.init_ui()


    def init_ui(self):
        self.setGeometry(QtCore.QRect(10,20,700,700))
        self.setFont(QtGui.QFont("Calibri",10)) 
        self.faqtree = QtWidgets.QTreeWidget(self)   
        self.faqtree.setHeaderLabel('FAQ')     
        self.faqtree.setGeometry(500,200, 400, 300)
        self.faqtree.setUniformRowHeights(False)
        self.faqtree.setWordWrap(True)
        self.faqtree.setFont(QtGui.QFont("Calibri",10))        
        self.importfaq("soil")        
        self.faqtree.header().resizeSection(1,200)       
        self.faqtree.setItemDelegate(ItemWordWrap(self.faqtree)) # Sush:Important for word wrap
        self.faqtree.setVisible(False)
        
        self.tab_summary = QTextEdit()        
        self.tab_summary.setPlainText("This tab allows to add a new soil profile or modify an existing one. Soil profile is linked with an existing site. \
If the soil you are creating is located within the USA territory, data will be retrieved from the Natural Resources Conservation Services (NRCS) for the most \
prominent soil profile for that location.  You will have the ability to edit or delete the values.  A soil profile can have one or more layers, to add or delete \
a soil layer, select the entire row and right click. It will open a dialog box with simple instructions. Once changes are done, please make sure to press the \
UPDATE/SAVE button.")
        self.tab_summary.setReadOnly(True)  
        self.tab_summary.setMaximumHeight(80) # need it        
        self.tab_summary.setAlignment(QtCore.Qt.AlignTop)
        self.tab_summary.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded) 
        self.tab_summary.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.tab_summary.setFrameShape(QtWidgets.QFrame.NoFrame)      
        self.helpcheckbox = QCheckBox("Turn FAQ on?")
        self.helpcheckbox.setChecked(False)
        self.helpcheckbox.stateChanged.connect(self.controlfaq)
        
        self.vl1 = QVBoxLayout()
        self.vl2 = QVBoxLayout()
        self.hl1 = QHBoxLayout()
        self.hl2 = QHBoxLayout()
        self.mainlayout1 = QGridLayout()
        self.spacer = QSpacerItem(10,10, QSizePolicy.Minimum, QSizePolicy.Expanding)
        self.hl1.addWidget(self.tab_summary)
        self.hl1.setContentsMargins(0,0,0,0)
        self.hl1.setSpacing(0)

        self.save_update_button = QPushButton("Save")
        self.delete_button = QPushButton("Delete")
        self.currentsoillabel = QLabel("Soil Name:")
        self.soilname2 = QLineEdit()
        self.system_msg = QLineEdit()
        self.system_msg.setFrame(False)
        self.save_update_button.setVisible(False)
        self.soilname2.setVisible(False)
        self.delete_button.setVisible(False)
        self.currentsoillabel.setVisible(False)
        self.hl2.addWidget(self.currentsoillabel)        
        self.hl2.addWidget(self.soilname2)
        self.hl2.addWidget(self.save_update_button)
        self.hl2.addWidget(self.delete_button)
        
        ## main sub tab 
        self.soillists = read_soilDB()
        self.soillistlabel2 = QLabel("Soil List")
        self.sitelabel = QLabel("Site List")

        self.soilcombo = QComboBox()
        self.sitecombo = QComboBox()
        self.soilselectionlabel= QLabel("Soil Properties")
        self.soiltable1 = QTableWidget()
        self.soiltable1.verticalHeader().setContextMenuPolicy(Qt.CustomContextMenu)
        self.soiltable1.verticalHeader().customContextMenuRequested.connect(self.soiltableverticalheader_popup)
        self.vl2.addWidget(self.soilselectionlabel)
        self.soilselectionlabel.setVisible(False)
        self.soiltable1.setVisible(False)
        self.sitecombo.setVisible(False)
        self.sitelabel.setVisible(False)
 
        self.soiltable1.horizontalScrollBar().setStyleSheet("QScrollBar:: horizontal {border: 2px solid grey; background: lightgray; height: 15px; \
                                                             margin: 0px 20px 0 20px;} \
                                                             QScrollBar::handle:horizontal {background: #32CC99; min-width: 20px;} \
                                                             QScrollBar::add-line:horizontal {border: 2px solid grey; background: none; width: 20px; \
                                                             subcontrol-position: right; subcontrol-origin: margin;} \
                                                             QScrollBar::sub-line:horizontal {border: 2px solid grey; background: none; width: 20px; \
                                                             subcontrol-position: left; subcontrol-origin: margin;} \
                                                             QScrollBar::left-arrow:horizontal, {border: 2px solid grey; width: 3px; height: 3px; \
                                                             background: white;} \
                                                             QScrollBar::right-arrow:horizontal, {border: 2px solid grey; width: 3px; height: 3px; \
                                                             background: white;}")

        self.soilcombo.addItem("Select From List")
        self.soilcombo.addItem("Add New Soil")
        for key in sorted(self.soillists):            
            self.soilcombo.addItem(key)

        self.soilcombo.currentIndexChanged.connect(self.showsoildetailscombo,self.soilcombo.currentIndex())
        self.soilpagegl = QGridLayout()
        self.soilpagegl.setSpacing(1) 
        self.soilpagegl.setHorizontalSpacing(5)
        self.soilpagegl.setVerticalSpacing(5)
        self.soilpagegl.addWidget(self.soillistlabel2,2,0)
        self.soilpagegl.addWidget(self.soilcombo,2,1)
        self.soilpagegl.addWidget(self.sitelabel,3,0)
        self.soilpagegl.addWidget(self.sitecombo,3,1)
        self.soilpagegl.addLayout(self.vl2,5,0,-1,-1)        
        self.soilpagegl.addWidget(self.soiltable1,5,1,-1,-1)
        self.vl1.setContentsMargins(1,1,1,1)
        self.vl1.addLayout(self.hl1)        
        self.vl1.addItem(self.spacer)
        self.vl1.addWidget(self.helpcheckbox)
        self.vl1.addLayout(self.soilpagegl)
        self.vl1.addLayout(self.hl2)
        self.system_msg.setReadOnly(True)
        self.vl1.addWidget(self.system_msg)
        self.vl1.addItem(self.spacer)
        self.vl1.setAlignment(QtCore.Qt.AlignTop)
        self.mainlayout1.addLayout(self.vl1,0,0)
        self.mainlayout1.setColumnStretch(0,3)
        self.mainlayout1.addWidget(self.faqtree,0,4)
        self.setLayout(self.mainlayout1)
        self.show()

    def loadSoilProfile(self,value):
        if self.soilcombo.itemText(self.soilcombo.currentIndex()) == "Add New Soil":
            # Get site lat lon
            #site_tuple = extract_sitedetails(self.sitecombo.itemText(value))   
            site_tuple = extract_sitedetails(self.sitecombo.itemText(self.sitecombo.currentIndex()))   
            lat = site_tuple[1]
            lon = site_tuple[2]

            # Get soil profile from NRCS website
            lonLat = str(lon) + " " + str(lat)
            url="https://SDMDataAccess.nrcs.usda.gov/Tabular/SDMTabularService.asmx"
            headers = {'content-type': 'text/xml'}
            body = """<?xml version="1.0" encoding="utf-8"?>
                      <soap:Envelope xmlns:soap="http://www.w3.org/2003/05/soap-envelope" xmlns:sdm="http://SDMDataAccess.nrcs.usda.gov/Tabular/SDMTabularService.asmx">
                      <soap:Header/>
                      <soap:Body>
                          <sdm:RunQuery>
                              <sdm:Query>SELECT co.cokey as cokey, ch.chkey as chkey, comppct_r as prcent, slope_r, slope_h as slope, hzname, hzdepb_r as depth, 
                                         awc_r as awc, claytotal_r as clay, silttotal_r as silt, sandtotal_r as sand, om_r as OM, dbthirdbar_r as dbthirdbar, 
                                         wthirdbar_r/100 as th33, (dbthirdbar_r-(wthirdbar_r/100)) as bd FROM sacatalog sc
                                         FULL OUTER JOIN legend lg  ON sc.areasymbol=lg.areasymbol
                                         FULL OUTER JOIN mapunit mu ON lg.lkey=mu.lkey
                                         FULL OUTER JOIN component co ON mu.mukey=co.mukey
                                         FULL OUTER JOIN chorizon ch ON co.cokey=ch.cokey
                                         FULL OUTER JOIN chtexturegrp ctg ON ch.chkey=ctg.chkey
                                         FULL OUTER JOIN chtexture ct ON ctg.chtgkey=ct.chtgkey
                                         FULL OUTER JOIN copmgrp pmg ON co.cokey=pmg.cokey
                                         FULL OUTER JOIN corestrictions rt ON co.cokey=rt.cokey
                                         WHERE mu.mukey IN (SELECT * from SDA_Get_Mukey_from_intersection_with_WktWgs84('point(""" + lonLat + """)')) order by co.cokey, ch.chkey, prcent, depth
                              </sdm:Query>
                          </sdm:RunQuery>
                       </soap:Body>
                       </soap:Envelope>"""

            response = requests.post(url,data=body,headers=headers)
            # Put query results in dictionary format
            my_dict = xmltodict.parse(response.content)

            soilheader = ["Bottom depth (cm)","OM (%)","NO3 (ppm)","NH4 (ppm)","HNew","Unit Type","Tmpr (C)","Sand (%)","Silt (%)","Clay (%)",\
                          "BD (g/cm3)","TH33 (cm3/cm3)","TH1500 (cm3/cm3)","thr","ths","tha","th","Alfa","n","Ks","Kk","thk"]
            self.soiltable1.setVisible(True)                
            self.save_update_button.setVisible(True)
            self.soilname2.setVisible(True)
            self.delete_button.setVisible(False)
            self.currentsoillabel.setVisible(False)
            self.soilselectionlabel.setVisible(False)
            self.sitecombo.setEnabled(True) 
            #self.sitecombo.currentIndexChanged.connect(self.loadSoilProfile,self.sitecombo.currentIndex())

            self.save_update_button.setText("SaveAs")
            self.soilname2.setText("Provide soil name")
            self.soilname2.setReadOnly(False)

            self.soiltable1.clear()
            self.soiltable1.setRowCount(0)
            self.soiltable1.setRowCount(1)
            self.soiltable1.setAlternatingRowColors(True)
            self.soiltable1.setColumnCount(22)
            self.soiltable1.setHorizontalHeaderLabels(soilheader)
  
            # Create and populate initType combo
            self.comboInitType = QComboBox()          
            self.comboInitType.addItem("m") # val = 1
            self.comboInitType.addItem("w") # val = 2

            # Convert from dictionary to dataframe format
            try:
                soil_df = pd.DataFrame.from_dict(my_dict['soap:Envelope']['soap:Body']['RunQueryResponse']['RunQueryResult']['diffgr:diffgram']['NewDataSet']['Table'])

                # Drop columns where all values are None or NaN
                soil_df = soil_df.dropna(axis=1, how='all')
                soil_df = soil_df[soil_df.chkey.notnull()]

                # Drop unecessary columns
                soil_df = soil_df.drop(['@diffgr:id', '@msdata:rowOrder', '@diffgr:hasChanges'], axis=1)

                # Drop duplicate rows
                soil_df = soil_df.drop_duplicates()

                # Convert prcent and depth column from object to float
                soil_df['prcent'] = soil_df['prcent'].astype(float)
                soil_df['depth'] = soil_df['depth'].astype(float)

                # Select rows with max prcent
                soil_df = soil_df[soil_df.prcent == soil_df.prcent.max()]

                # Sort rows by depth
                soil_df = soil_df.sort_values(by=['depth'])

                # Check for rows with NaN values
                soil_df_with_NaN = soil_df[soil_df.isnull().any(axis=1)]
                depth = ", ".join(soil_df_with_NaN["depth"].astype(str))
                if len(depth) > 0:
                    messageUser("Layers with the following depth " + depth + " were deleted.")
                    soil_df = soil_df.dropna()

                ### here add the logic for add soil layer
                ## check if all the existing layer has valid data. If yes, then activate the "Add Soil Layer" 
                #button else keep is grayed out
                for index, row in soil_df.iterrows():
                    # Create and populate initType combo
                    self.comboInitType = QComboBox()          
                    self.comboInitType.addItem("m") # val = 1
                    self.comboInitType.addItem("w") # val = 2

                    ccurentrow = self.soiltable1.rowCount()
                    self.soiltable1.insertRow(ccurentrow)
                    for col in range(22):
                        if col == 0:
                            self.soiltable1.setItem(ccurentrow-1,col,QTableWidgetItem(str(row['depth'])))
                        elif col == 1:
                            self.soiltable1.setItem(ccurentrow-1,col,QTableWidgetItem(str(row['OM'])))
                        elif col == 5:    
                            self.soiltable1.setCellWidget(ccurentrow-1,col,self.comboInitType)
                        elif col == 7:
                            self.soiltable1.setItem(ccurentrow-1,col,QTableWidgetItem(str(row['sand'])))
                        elif col == 8:
                            self.soiltable1.setItem(ccurentrow-1,col,QTableWidgetItem(str(row['silt'])))
                        elif col == 9:
                            self.soiltable1.setItem(ccurentrow-1,col,QTableWidgetItem(str(row['clay'])))
                        elif col == 10:
                            self.soiltable1.setItem(ccurentrow-1,col,QTableWidgetItem(str(row['bd'])))
                        elif col == 11:
                            self.soiltable1.setItem(ccurentrow-1,col,QTableWidgetItem(str(row['th33'])))
                        else:
                            self.soiltable1.setItem(ccurentrow-1,col,QTableWidgetItem("-1"))
            except KeyError:
                print("No data!")
                self.soiltable1.clear()
                self.soiltable1.setRowCount(0)
                self.soiltable1.setRowCount(1)
                self.soiltable1.setAlternatingRowColors(True)
                self.soiltable1.setColumnCount(22)
                self.soiltable1.setHorizontalHeaderLabels(soilheader)
               # Create and populate initType combo
                self.comboInitType = QComboBox()          
                self.comboInitType.addItem("m") # val = 1
                self.comboInitType.addItem("w") # val = 2

                # This list holds the soil long table default values
                soillonglist = [0,0,0,0,-200,1,0,0,0,0,0,-1,-1,-1,-1,-1,-1,-1,-1,-1,-1,-1]
                colnum=0
                for val in soillonglist:
                    if colnum == 5:    
                        if(val == 1):
                            matchedindex = self.comboInitType.findText("m")
                        self.comboInitType.setCurrentIndex(matchedindex)
                        self.soiltable1.setCellWidget(0,colnum,self.comboInitType)
                    else:
                        self.soiltable1.setItem(0,colnum,QTableWidgetItem(str(val)))
                    colnum=colnum+1


    def showsoildetailscombo(self,value):
        print("**** debug: showsoildetailscombo called,itemtext=",\
              self.soilcombo.itemText(self.soilcombo.currentIndex()))
        
        # Selected "Select from list"
        if self.soilcombo.itemText(self.soilcombo.currentIndex()) == "Select From List":
            self.soiltable1.setVisible(False)                
            self.save_update_button.setVisible(False)
            self.soilname2.setVisible(False)
            self.delete_button.setVisible(False)
            self.currentsoillabel.setVisible(False)
            self.sitecombo.setVisible(False)
            self.sitelabel.setVisible(False)
            self.soilselectionlabel.setVisible(False)
        else:
            self.sitelists = read_sitedetailsDB()
            self.sitecombo.clear()
            self.sitecombo.addItem("Select From List")
            for key in sorted(self.sitelists):            
                self.sitecombo.addItem(key)

            soilheader = ["Bottom depth (cm)","OM (%)","NO3 (ppm)","NH4 (ppm)","HNew","Unit Type","Tmpr (C)","Sand (%)","Silt (%)","Clay (%)",\
                          "BD (g/cm3)","TH33 (cm3/cm3)","TH1500 (cm3/cm3)","thr","ths","tha","th","Alfa","n","Ks","Kk","thk"]

            self.sitecombo.setVisible(True)
            self.sitelabel.setVisible(True)

            # Selected "add new soil"
            if self.soilcombo.itemText(self.soilcombo.currentIndex()) == "Add New Soil":
                print("New soil!")
                self.soiltable1.setVisible(False)                
                self.save_update_button.setVisible(False)
                self.soilname2.setVisible(False)
                self.delete_button.setVisible(False)
                self.currentsoillabel.setVisible(False)
                self.soilselectionlabel.setVisible(False)
                self.sitecombo.setEnabled(True)
                self.sitecombo.setCurrentIndex(self.sitecombo.findText("Select From List"))
                self.sitecombo.currentIndexChanged.connect(self.loadSoilProfile,self.sitecombo.currentIndex())

                ### here add the logic for add soil layer
                ## check if all the existing layer has valid data. If yes, then activate the "Add Soil Layer" 
                #button else keep is grayed out
                self.soiltable1.clear()
                self.soiltable1.setRowCount(0)
                self.soiltable1.setRowCount(1)
                self.soiltable1.setAlternatingRowColors(True)
                self.soiltable1.setColumnCount(22)
                self.soiltable1.setHorizontalHeaderLabels(soilheader)            
            else:
                self.soilselectionlabel.setVisible(True)
                self.soiltable1.setVisible(True)
                self.save_update_button.setVisible(True)
                self.soilname2.setVisible(True)
                self.delete_button.setVisible(True)
                self.currentsoillabel.setVisible(True)
                self.save_update_button.setText("Update")  
                self.soilname2.setText(self.soilcombo.itemText(value))  
                self.soilname2.setReadOnly(True)

                #print("soilname=",self.soilcombo.itemText(value))
                soillonglist = read_soillongDB(self.soilcombo.itemText(value)) 
                #print("soillonglist",soillonglist)
                sitename =  getSiteFromSoilname(self.soilcombo.itemText(value))
                #print("sitename=",sitename[0])
                self.sitecombo.setCurrentIndex(self.sitecombo.findText(sitename[0]))
                self.sitecombo.setEnabled(False)
          
                self.soiltable1.clear()
                self.soiltable1.setRowCount(0)
                self.soiltable1.setAlternatingRowColors(True)
                self.soiltable1.setColumnCount(22)
                self.soiltable1.setHorizontalHeaderLabels(soilheader)
                #print(soillonglist)
            
                for rrecord in soillonglist[0:21]:
                    ccurentrow = self.soiltable1.rowCount()
                    self.soiltable1.insertRow(ccurentrow)
                    colnum=0

                    # Create and populate initType combo
                    self.comboInitType = QComboBox()          
                    self.comboInitType.addItem("m") # val = 1
                    self.comboInitType.addItem("w") # val = 2

                    for ccolumn in rrecord:
                        if colnum == 1:
                            ccolumn = ccolumn * 100
                        if colnum == 5:  
                            if(ccolumn == 1):
                                matchedindex = self.comboInitType.findText("m")
                            else:
                                matchedindex = self.comboInitType.findText("w")
                            self.comboInitType.setCurrentIndex(matchedindex)
                            self.soiltable1.setCellWidget(ccurentrow,colnum,self.comboInitType)
                        else:
                            self.soiltable1.setItem(ccurentrow,colnum,QTableWidgetItem(str(ccolumn)))
                        colnum=colnum+1
            
                self.delete_button.clicked.connect(lambda:self.on_deletebuttonclick())

            self.save_update_button.clicked.connect(lambda:self.on_savebuttonclick())
            self.soiltable1.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)                                   
            self.soiltable1.resizeColumnsToContents()
            self.soiltable1.verticalHeader().setStretchLastSection(False)
            self.soiltable1.resizeRowsToContents()
            self.soiltable1.verticalHeader().setStretchLastSection(True)

            self.soiltable1.horizontalHeader().setSectionResizeMode(0,QHeaderView.ResizeToContents)
            self.soiltable1.horizontalHeader().setSectionResizeMode(1,QHeaderView.ResizeToContents)
            self.soiltable1.horizontalHeader().setSectionResizeMode(2,QHeaderView.ResizeToContents)
            self.soiltable1.horizontalHeader().setSectionResizeMode(3,QHeaderView.ResizeToContents)
            self.soiltable1.horizontalHeader().setSectionResizeMode(4,QHeaderView.ResizeToContents)
            self.soiltable1.horizontalHeader().setSectionResizeMode(5,QHeaderView.ResizeToContents)
            self.soiltable1.horizontalHeader().setSectionResizeMode(6,QHeaderView.ResizeToContents)
            self.soiltable1.horizontalHeader().setSectionResizeMode(7,QHeaderView.ResizeToContents)
            self.soiltable1.horizontalHeader().setSectionResizeMode(8,QHeaderView.ResizeToContents)  
            self.soiltable1.horizontalHeader().setSectionResizeMode(9,QHeaderView.ResizeToContents)  
            self.soiltable1.horizontalHeader().setSectionResizeMode(10,QHeaderView.ResizeToContents)  
            self.soiltable1.horizontalHeader().setSectionResizeMode(11,QHeaderView.ResizeToContents)
            self.soiltable1.horizontalHeader().setSectionResizeMode(12,QHeaderView.ResizeToContents)
            self.soiltable1.horizontalHeader().setSectionResizeMode(13,QHeaderView.ResizeToContents)
            self.soiltable1.horizontalHeader().setSectionResizeMode(14,QHeaderView.ResizeToContents)
            self.soiltable1.horizontalHeader().setSectionResizeMode(15,QHeaderView.ResizeToContents)
            self.soiltable1.horizontalHeader().setSectionResizeMode(16,QHeaderView.ResizeToContents)
            self.soiltable1.horizontalHeader().setSectionResizeMode(17,QHeaderView.ResizeToContents)
            self.soiltable1.horizontalHeader().setSectionResizeMode(18,QHeaderView.ResizeToContents)  
            self.soiltable1.horizontalHeader().setSectionResizeMode(19,QHeaderView.ResizeToContents)  
            self.soiltable1.horizontalHeader().setSectionResizeMode(20,QHeaderView.ResizeToContents)   
            self.soiltable1.horizontalHeader().setSectionResizeMode(21,QHeaderView.ResizeToContents)   

        # This takes care of enter behaviour
        for key in (QtCore.Qt.Key_Return, QtCore.Qt.Key_Enter):
            QtWidgets.QShortcut(key, self.soiltable1, partial(self.soiltable1.focusNextPrevChild, True))

          
    def getsoilrowinfo(self,rownum):
        currentrow_data = []
        #print("debug getsoilrowinfo: rownum, rowcount:",rownum,self.soiltable1.rowCount() )
        if rownum >=0 and rownum < self.soiltable1.rowCount():
            colnum = 0            
            for ccolumn in range(0,self.soiltable1.columnCount()):
                if(colnum == 5):
                    if(self.comboInitType.currentText() == "m"):
                        val = 1
                    if(self.comboInitType.currentText() == "w"):
                        val = 2
                    currentrow_data.append(float(val))
                else:
                    currentrow_data.append(float(self.soiltable1.item(rownum,ccolumn).text()))
                colnum = colnum + 1
        return currentrow_data


    def deletethisrow(self):
        '''
        deletes the current row
        '''
        where2insertrow = self.soiltable1.currentRow()
        self.soiltable1.removeRow(where2insertrow)        
        howmanyrows = self.soiltable1.rowCount()
        #print("after howmanyrows=",howmanyrows)
        if howmanyrows == 0:
            self.soiltable1.insertRow(howmanyrows)
            for rrecord in soillonglist:
                colnum=0 #1
                # Create and populate initType combo
                self.comboInitType = QComboBox()          
                self.comboInitType.addItem("m") # val = 1
                self.comboInitType.addItem("w") # val = 2

                for ccolumn in rrecord:
                    if(colnum == 5):
                        if(ccolumn == 1):
                            matchedindex = self.comboInitType.findText("m")
                        else:
                            matchedindex = self.comboInitType.findText("w")
                        self.comboInitType.setCurrentIndex(matchedindex)
                        self.soiltable1.setCellWidget(ccurentrow,colnum,self.comboInitType)
                    else:
                        self.soiltable1.setItem((howmanyrows),colnum,QTableWidgetItem(str(ccolumn)))

                    colnum=colnum+1

        self.soiltable1.setItem(howmanyrows,0,QTableWidgetItem(str(-99)))                    
        self.soiltable1.setMaximumHeight(self.soiltable1.verticalHeader().length()*1.25)
        self.soiltable1.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.soiltable1.resizeColumnsToContents()
        self.soiltable1.verticalHeader().setStretchLastSection(False)
        self.soiltable1.resizeRowsToContents()
        self.soiltable1.verticalHeader().setStretchLastSection(True)
        self.soiltable1.resizeColumnsToContents() 


    def duplicaterowabove(self):
        '''
        duplicate a row above
        '''
        # saving the states from these 3 layers
        currentrow_data = self.getsoilrowinfo(self.soiltable1.currentRow())
        previousrow_data = self.getsoilrowinfo(self.soiltable1.currentRow()-1)

        where2insertrow = 0
        where2insertrow = self.soiltable1.currentRow()

        self.soiltable1.insertRow(where2insertrow)        
        colnum=0 #1
        # Create and populate initType combo
        self.comboInitType = QComboBox()          
        self.comboInitType.addItem("m") # val = 1
        self.comboInitType.addItem("w") # val = 2

        for ccolumn in  currentrow_data:               
            if(colnum == 5):
                if(ccolumn == 1):
                    matchedindex = self.comboInitType.findText("m")
                else:
                    matchedindex = self.comboInitType.findText("w")
                self.comboInitType.setCurrentIndex(matchedindex)
                self.soiltable1.setCellWidget(where2insertrow,colnum,self.comboInitType)
            else:
                self.soiltable1.setItem(where2insertrow,colnum,QTableWidgetItem(str(ccolumn)))

            colnum=colnum+1
            # initialize the depth for the new layer to be greater than previous layer (if no 3rd layer 
            # exist) or middle point of 1st and 3rd layer
            
        newdepth = currentrow_data[0]/2
        if len(previousrow_data) >0:
            newdepth = (currentrow_data[0]+ previousrow_data[0])/2                        

        self.soiltable1.setItem(where2insertrow,0,QTableWidgetItem(str(newdepth)))            
        self.soiltable1.setMaximumHeight(self.soiltable1.verticalHeader().length()*1.25)
        self.soiltable1.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.soiltable1.resizeColumnsToContents()
        self.soiltable1.verticalHeader().setStretchLastSection(False)
        self.soiltable1.resizeRowsToContents()
        self.soiltable1.verticalHeader().setStretchLastSection(True)
        self.soiltable1.resizeColumnsToContents() 


    def duplicaterowbelow(self):
        '''
        duplicate a row below
        '''
        # saving the states from these 3 layers
        currentrow_data = self.getsoilrowinfo(self.soiltable1.currentRow())
        nextrow_data = self.getsoilrowinfo(self.soiltable1.currentRow()+1)

        where2insertrow = 0
        where2insertrow = self.soiltable1.currentRow()+1
        self.soiltable1.insertRow(where2insertrow)        
        colnum=0               
        # Create and populate initType combo
        self.comboInitType = QComboBox()          
        self.comboInitType.addItem("m") # val = 1
        self.comboInitType.addItem("w") # val = 2

        for ccolumn in  currentrow_data:               
            if(colnum == 5):
                if(ccolumn == 1):
                    matchedindex = self.comboInitType.findText("m")
                else:
                    matchedindex = self.comboInitType.findText("w")
                self.comboInitType.setCurrentIndex(matchedindex)
                self.soiltable1.setCellWidget(where2insertrow,colnum,self.comboInitType)
            else:
                self.soiltable1.setItem(where2insertrow,colnum,QTableWidgetItem(str(ccolumn)))

            colnum=colnum+1

        newdepth = currentrow_data[0] + 1.0
        if len(nextrow_data) >0:
            newdepth = (currentrow_data[0]+ nextrow_data[0])/2                        

        self.soiltable1.setItem(where2insertrow,0,QTableWidgetItem(str(newdepth)))            
        self.soiltable1.setMaximumHeight(self.soiltable1.verticalHeader().length()*1.25)
        self.soiltable1.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.soiltable1.resizeColumnsToContents()
        self.soiltable1.verticalHeader().setStretchLastSection(False)
        self.soiltable1.resizeRowsToContents()
        self.soiltable1.verticalHeader().setStretchLastSection(True)
        self.soiltable1.resizeColumnsToContents() 


    def soiltableverticalheader_popup(self, pos):
        '''
        pop menu items will come here
        '''
        #print("soiltableverticalheader_popup debuga",len(self.soiltable1.selectionModel().selectedRows()))
        #print("soiltableverticalheader_popup debugb", len(self.soiltable1.selectedIndexes()))
        if (len(self.soiltable1.selectionModel().selectedRows()) !=1):
            return True

        menu = QMenu()
        duplicaterowbelowaction = menu.addAction("Duplicate this layer below")
        duplicaterowaboveaction = menu.addAction("Duplicte this layer above")
        deletethisrowaction = menu.addAction("Delete this row")
        action = menu.exec_(QtGui.QCursor.pos())
        
        if action == duplicaterowaboveaction:
            #print("debug: duplicate above")
            self.duplicaterowabove()

        if action == duplicaterowbelowaction:
            #print("debug: duplicate below")
            self.duplicaterowbelow()

        if action == deletethisrowaction:
            #print("debug: duplicate below")
            self.deletethisrow()


    def importfaq(self, thetabname=None):        
        faqlist = read_FaqDB(thetabname) 
        faqcount=0
        
        for item in faqlist:
            roottreeitem = QTreeWidgetItem(self.faqtree)
            roottreeitem.setText(0,item[2])
            childtreeitem = QTreeWidgetItem()
            childtreeitem.setText(0,item[3])
            roottreeitem.addChild(childtreeitem)


    def controlfaq(self):                
        if self.helpcheckbox.isChecked():
            self.faqtree.setVisible(True)
        else:
            self.faqtree.setVisible(False)

        
    def resource_path(self,relative_path):
        """
        Get absolute path to resource, works for dev and for PyInstaller 
        """
        base_path = getattr(sys, '_MEIPASS', os.path.dirname(os.path.abspath(__file__)))
        return os.path.join(base_path, relative_path)  


    @pyqtSlot()
    def on_deletebuttonclick(self):
        '''
        aim: to delete the soil file, on display, from the database
        Under process. Have to clean the entries from hgrid, gridratiotable, soil, soil_long etc. Refresh 
        the soil tab screen
        from table soil, retrieve the id (o_sid), o_gridratio_id.
        from table soil_long, delete all records with o_sid == id
        from table gridratio, delete record with gridratio_id = o_gridratio_id
        '''
        check_and_delete_soilDB(self.soilname2.text())
        self.reset_view()


    def reset_view(self):
        '''
        This will Block Signals, reset combobox entries. Unblock signals
        '''
        self.save_update_button.setText("Blank")
        tmp_index = self.soilcombo.currentIndex()
        self.soilcombo.blockSignals(True)
        self.soilcombo.clear()
        self.soillists = read_soilDB()
        self.soilcombo.addItem("Select From List")
        self.soilcombo.addItem("Add New Soil")
        for key in sorted(self.soillists):            
            self.soilcombo.addItem(key)

        self.soilselectionlabel.setVisible(False)
        self.soiltable1.setVisible(False) 
        self.soiltable1.clear()
        self.soiltable1.reset()
        self.soiltable1.setRowCount(0)
        self.system_msg.clear()
        self.system_msg.setFrame(False)
        self.save_update_button.setVisible(False)
        self.soilname2.setVisible(False)
        self.delete_button.setVisible(False)
        self.currentsoillabel.setVisible(False)  
        self.soilcombo.blockSignals(False)  
        self.sitecombo.setVisible(False)
        self.sitelabel.setVisible(False)


    @pyqtSlot()
    def on_savebuttonclick(self):
        '''
        aim: to save the soil data from the soil tab
        '''
        print("debug: SoilTab::on_savebuttonclick(): savebutton_name=",self.save_update_button.text())
        soilgrid_list =[1,2,3,4.5,6,8.5,11,14,19,23,27,33,38]
        soilgridratio_list =[1.6,0.05,2.1,2,10,23,1]
        next_gridratio_id =0
        self.system_msg.clear()
        #find is it update or save
        if self.save_update_button.text() == "SaveAs":
            print("Debug soiltab:on_savebuttonclick: self.soilname2.text=",self.soilname2.text())
            soilname = str(self.soilname2.text())
            if (soilname == "" or soilname == "Provide soil name"):
                messageUser("Please, provide soil name.")
                return False
            # Get site_id
            site_tuple = extract_sitedetails(self.sitecombo.itemText(self.sitecombo.currentIndex()))   
            site_id = str(site_tuple[0])
            # proceed with creating ids for other tables - saveas logic will come here
            # save soilgridratiolist and preserve the value of new gridratio_id        
            next_gridratio_id = insert_soilgridratioDB(tuple(soilgridratio_list))
            #inserts the soil, gridratio
            if not check_and_insert_soilDB(soilname,site_id,next_gridratio_id):
                print("This name already exist.")
                return False 
        elif self.save_update_button.text() == "Update":
            delete_soillong(self.soilname2.text())

        for rrow in range(self.soiltable1.rowCount()): 
            retrieved_datalist= []
            colnum = 0            
            for ccol in range(self.soiltable1.columnCount()):
                #if self.soiltable1.item(rrow,ccol):
                    if(colnum == 5):
                        opt = self.soiltable1.cellWidget(rrow,ccol).currentText()
                        if(opt == "m"):
                            val = 1
                        if(opt == "w"):
                            val = 2
                        retrieved_datalist.append(float(val))
                    else:
                        retrieved_datalist.append(self.soiltable1.item(rrow,ccol).text())
                    colnum = colnum + 1
            #print("debug:soil_widget:on_savebutton_click(): working on layer#",rrow," ",retrieved_datalist)
            insert_into_soillong(self.soilname2.text(), tuple(retrieved_datalist))
        self.reset_view()
