public class SignalPlotter extends WindowAdapter {
	// configure logging
	static {
    	System.setProperty("java.util.logging.SimpleFormatter.format",
                "[%1$tF %1$tT] %4$-7s %2$s %5$s %6$s %n");
    }
    private static final Logger LOGGER = Logger.getLogger(SignalPlotter.class.getName());
	private static final ConsoleHandler handler = new ConsoleHandler();
	static {
    	LOGGER.addHandler(handler);
    	LOGGER.setUseParentHandlers(false);
    	LOGGER.setLevel(Level.FINE);
    	handler.setLevel(Level.FINE);
    }

    public static final String version = "7.1";

    private String oldFolder = ".\\";
    private String oldFileName = "";
    private String oldEntryName = "";

    private JFrame frame;
    private JTextField textFieldFileName;
    private JTextArea textArea_1;
    private SignalChartPanel chartPanel;
    private JList<String> listOfNames = new JList<String>();
    private JList<SignalChartPanel> listOfCharts = new JList<SignalChartPanel>();

    /**
     * Launch the application.
     */
    public static void main(String[] args) {
        EventQueue.invokeLater(new Runnable() {
            public void run() {
                try {
                    //LOGGER.log(Level.FINE, "SignalPlotter " + version + " started");
                	SignalPlotter window = new SignalPlotter();
                    window.frame.setVisible(true);
                	//Logger.getLogger("").setLevel(Level.FINE);
                	//Logger.getLogger("").getHandlers()[0].setLevel(Level.FINE);
                	LOGGER.log(Level.FINE, "SignalPlotter " + version + " started");
                } catch (Exception ex) {
                    LOGGER.log(Level.SEVERE, " run exceptoin");
                    LOGGER.log(Level.INFO, "Exception info ", ex);
                }
            }
        });
    }

    /**
     * Create the application. Default constructor.
     */
    public SignalPlotter() {
        initialize();
    }

    /**
     * Initialize the contents of the frame.
     */
    private void initialize() {
        frame = new JFrame();
        //frame.setResizable(false);
        frame.setBounds(100, 100, 600, 600);
        //frame.setDefaultCloseOperation(JFrame.EXIT_ON_CLOSE);
        frame.setDefaultCloseOperation(JFrame.DISPOSE_ON_CLOSE);
        frame.addWindowListener(this);
        SpringLayout springLayout = new SpringLayout();
        frame.getContentPane().setLayout(springLayout);

        // Open file panel
        JPanel panelOpenFile = new JPanel();
        springLayout.putConstraint(SpringLayout.NORTH, panelOpenFile, -65,
                SpringLayout.SOUTH, frame.getContentPane());
        springLayout.putConstraint(SpringLayout.WEST, panelOpenFile, 5,
                SpringLayout.WEST, frame.getContentPane());
        springLayout.putConstraint(SpringLayout.SOUTH, panelOpenFile, -5,
                SpringLayout.SOUTH, frame.getContentPane());
        springLayout.putConstraint(SpringLayout.EAST, panelOpenFile, -270,
                SpringLayout.EAST, frame.getContentPane());
        panelOpenFile.setBorder(new TitledBorder(new EtchedBorder(
                EtchedBorder.LOWERED, null, null), "File",
                TitledBorder.LEADING, TitledBorder.TOP, null, null));
        frame.getContentPane().add(panelOpenFile);
        SpringLayout sl_panelOpenFile = new SpringLayout();
        panelOpenFile.setLayout(sl_panelOpenFile);

        // Open file name text field in open file panel 
        textFieldFileName = new JTextField();
        sl_panelOpenFile.putConstraint(SpringLayout.NORTH, textFieldFileName,
                5, SpringLayout.NORTH, panelOpenFile);
        sl_panelOpenFile.putConstraint(SpringLayout.SOUTH, textFieldFileName,
                -5, SpringLayout.SOUTH, panelOpenFile);
        sl_panelOpenFile.putConstraint(SpringLayout.EAST, textFieldFileName,
                -55, SpringLayout.EAST, panelOpenFile);
        sl_panelOpenFile.putConstraint(SpringLayout.WEST, textFieldFileName, 5,
                SpringLayout.WEST, panelOpenFile);
        panelOpenFile.add(textFieldFileName);

        // Select file button in open file panel 
        JButton btnOpenFile = new JButton("...");
        sl_panelOpenFile.putConstraint(SpringLayout.NORTH, btnOpenFile, 5,
                SpringLayout.NORTH, panelOpenFile);
        sl_panelOpenFile.putConstraint(SpringLayout.SOUTH, btnOpenFile, -5,
                SpringLayout.SOUTH, panelOpenFile);
        sl_panelOpenFile.putConstraint(SpringLayout.EAST, btnOpenFile, -5,
                SpringLayout.EAST, panelOpenFile);
        sl_panelOpenFile.putConstraint(SpringLayout.WEST, btnOpenFile, 5,
                SpringLayout.EAST, textFieldFileName);
        // Click event for select file button - open file dialog 
        btnOpenFile.addMouseListener(new MouseAdapter() {
            @Override
            public void mouseClicked(MouseEvent arg0) {
                JFileChooser fileChooser = new JFileChooser();
                FileNameExtensionFilter filter = new FileNameExtensionFilter(
                        "Signal or archieve", "txt", "zip");
                fileChooser.setFileFilter(filter);
                fileChooser.setCurrentDirectory(new File(oldFolder));
                int result = fileChooser.showDialog(null, "Open signal or archieve");
                if (result == JFileChooser.APPROVE_OPTION) {
                    File file = fileChooser.getSelectedFile();
                    textFieldFileName.setText(file.getPath());
                    readFile(file.getPath());
                    oldFolder = file.getParent();
                }
            }
        });
        panelOpenFile.add(btnOpenFile);

        // List of signals in Zip file
        JScrollPane scrollPane_1 = new JScrollPane();
        springLayout.putConstraint(SpringLayout.NORTH, scrollPane_1, 0,
                SpringLayout.NORTH, panelOpenFile);
        springLayout.putConstraint(SpringLayout.WEST, scrollPane_1, 5,
                SpringLayout.EAST, panelOpenFile);
        springLayout.putConstraint(SpringLayout.SOUTH, scrollPane_1, 0,
                SpringLayout.SOUTH, panelOpenFile);
        springLayout.putConstraint(SpringLayout.EAST, scrollPane_1, -5,
                SpringLayout.EAST, frame.getContentPane());
        frame.getContentPane().add(scrollPane_1);
        // List control for signal names
        DefaultListModel<String> model = new DefaultListModel<String>();
        listOfNames = new JList<String>(model);
        // ListSelectioEvent processing for List control
        listOfNames.addListSelectionListener(new ListSelectionListener() {
            public void valueChanged(ListSelectionEvent arg0) {
                if (!arg0.getValueIsAdjusting()) {
                    readFile(oldFileName, listOfNames.getSelectedValue());
                    //readParamZip(oldFileName);
                    //readFileZip(oldFileName);
                    //chartPanel.setChartParam();
                }
            }
        });
        scrollPane_1.setViewportView(listOfNames);

        // Tabbed pane for Plot, ErorrList, Log, etc..
        JTabbedPane tabbedPane = new JTabbedPane(JTabbedPane.TOP);
        springLayout.putConstraint(SpringLayout.NORTH, tabbedPane, 5,
                SpringLayout.NORTH, frame.getContentPane());
        springLayout.putConstraint(SpringLayout.WEST, tabbedPane, 5,
                SpringLayout.WEST, frame.getContentPane());
        springLayout.putConstraint(SpringLayout.SOUTH, tabbedPane, -5,
                SpringLayout.NORTH, panelOpenFile);
        springLayout.putConstraint(SpringLayout.EAST, tabbedPane, -5,
                SpringLayout.EAST, frame.getContentPane());
        frame.getContentPane().add(tabbedPane);

        JSplitPane splitPane1 = new JSplitPane();
        splitPane1.setResizeWeight(0.5);
        splitPane1.setOrientation(JSplitPane.VERTICAL_SPLIT);
        tabbedPane.addTab("Text", null, splitPane1, null);
        tabbedPane.setEnabledAt(0, true);

        // Scrollable Text Tab
        JScrollPane scrollPane1 = new JScrollPane();
        splitPane1.setLeftComponent(scrollPane1);

        JTextArea textArea_1 = new JTextArea();
        textArea_1.setEditable(false);
        scrollPane1.setViewportView(textArea_1);
        JScrollPane scrollPane2 = new JScrollPane();
        splitPane1.setRightComponent(scrollPane2);

        this.textArea_1 = textArea_1;

        JLabel lblSignalProperties = new JLabel("Signal Properties");
        lblSignalProperties.setFont(new Font("Tahoma", Font.PLAIN, 14));
        lblSignalProperties.setHorizontalAlignment(SwingConstants.CENTER);
        scrollPane1.setColumnHeaderView(lblSignalProperties);

        JTextArea textArea_2 = new JTextArea();
        textArea_2.setEditable(false);
        scrollPane2.setViewportView(textArea_2);

        // Config Tab (unused)
        JPanel panel_2 = new JPanel();
        tabbedPane.addTab("Config", null, panel_2, null);
        // Check box (unused)
        JCheckBox chckbxNewCheckBox = new JCheckBox("New check box");
        panel_2.add(chckbxNewCheckBox);
        // Button (unused)
        JButton btnNewButton_1 = new JButton("New button");
        panel_2.add(btnNewButton_1);

        // Chart Tab
        chartPanel = new SignalChartPanel();
        tabbedPane.insertTab("Signal", null, chartPanel, null, 0);

        JScrollPane scrollPane = new JScrollPane();
        tabbedPane.addTab("Charts", null, scrollPane, null);
        DefaultListModel<SignalChartPanel> chartModel = new DefaultListModel<>();
        listOfCharts = new JList<>(chartModel); //new JList();
        scrollPane.setViewportView(listOfCharts);
        listOfCharts.setCellRenderer(new ChartCellRenderer());

        tabbedPane.setSelectedIndex(0);
    }

    @Override
    public void windowClosed(WindowEvent e) {
        saveConfig();
        System.exit(0);
    }

    @Override
    public void windowOpened(WindowEvent e) {
        restoreConfig();
    }

    private void restoreConfig() {
        Rectangle bounds = frame.getBounds();
        int index = 0;
        try {
            ObjectInputStream objIStrm = new ObjectInputStream(new FileInputStream("config.dat"));
            oldFolder = (String) objIStrm.readObject();
            oldFileName = (String) objIStrm.readObject();
            oldEntryName = (String) objIStrm.readObject();
            bounds = (Rectangle) objIStrm.readObject();
            index = (int) objIStrm.readObject();
            objIStrm.close();
            
            // set bounds of main window
            frame.setBounds(bounds);
  
            // open last signal
            if (!"".equals(oldFileName)) {
                String fileName = oldFileName;
                oldFileName = "";
                readFile(fileName);
                textFieldFileName.setText(fileName);
                if (fileName.endsWith(".zip")) {
                    listOfNames.setSelectedIndex(index);
                    listOfNames.ensureIndexIsVisible(index);
                    readFile(fileName, listOfNames.getSelectedValue());
                }
                chartPanel.setChartParam();
            }
        } catch (Exception ex) {
            LOGGER.log(Level.SEVERE, "Config resd error");
            LOGGER.log(Level.INFO, "Exception info", ex);
        }
    }

    private void saveConfig() {
        Rectangle bounds = frame.getBounds();
        try {
            ObjectOutputStream objOStrm = new ObjectOutputStream(new FileOutputStream("config.dat"));
            objOStrm.writeObject(oldFolder);
            objOStrm.writeObject(oldFileName);
            objOStrm.writeObject(oldEntryName);
            objOStrm.writeObject(bounds);
            objOStrm.writeObject(listOfNames.getSelectedIndex());
            objOStrm.close();
        } catch (IOException ex) {
            System.out.println("Exception : " + ex);
        }
    }

    private void readZipFileList(String fileName) {
        if (fileName == oldFileName) {
            return;
        }
        DefaultListModel<String> model = (DefaultListModel<String>) listOfNames.getModel();
        model.clear();
        List<String> signalList = readSignalList(fileName);
        for (String str : signalList) {
            model.addElement(str);
        }
        listOfNames.setVisible(true);

        DefaultListModel<SignalChartPanel> chartModel = (DefaultListModel<SignalChartPanel>) listOfCharts.getModel();
        chartModel.clear();
        for (String str : signalList) {
            SignalChartPanel chart = new SignalChartPanel();
            chart.readParameters(fileName, str);
            chart.readData(fileName, str);
            chart.setChartParam();
            chartModel.addElement(chart);
        }
    }

    public static List<String> readSignalList(String fileName) {
        //System.out.println("readSignalList " + fileName);
        LinkedList<String> list = new LinkedList<>();
        try {
            ZipBufferedReader zbr = new ZipBufferedReader(fileName);
            List<String> zipEntryList = zbr.readZipEntryList();
            for (String str : zipEntryList) {
                String match = ".+chan[0-9]+\\.txt$";
                String nonMatch = ".+paramchan[0-9]+\\.txt$";
                //System.out.println(str + " = " + str.matches(match));
                if (str.matches(match) && (!str.matches(nonMatch))) {
                    list.add(str);
                }
            }
            zbr.close();
        } catch (IOException ex) {
            LOGGER.log(Level.SEVERE, " exceptoin");
            LOGGER.log(Level.INFO, "Exception info", ex);
        }
        return list;
    }

    private void readFile(String fileName) {
        if (fileName == null || fileName == "") {
            return;
        }
        if (fileName.endsWith(".zip")) {
            readZipFileList(fileName);
            oldFileName = fileName;
            return;
        }

        DefaultListModel<String> model = (DefaultListModel<String>) listOfNames.getModel();
        model.clear();
        listOfNames.setVisible(false);

        if (fileName == oldFileName) {
            return;
        }

        chartPanel.readParameters(fileName);
        chartPanel.readData(fileName);
        chartPanel.setChartParam();

        textArea_1.setCaretPosition(0);
        oldFileName = fileName;
    }

    private void readFile(String fileName, String entryName) {
        if (entryName == null) {
            return;
        }
        if (oldEntryName == entryName) {
            return;
        }

        chartPanel.readParameters(fileName, entryName);
        chartPanel.readData(fileName, entryName);
        chartPanel.setChartParam();

        textArea_1.setCaretPosition(0);
        oldEntryName = entryName;
    }
}
