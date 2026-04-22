
// !! BUGs:
//  * When selecting a file with too long name, the button "File" is obstructed by the label and cannot be clicked.
//  * Error when trying to "import" a Python file with "-" in name.
//  * Start the app, select a HOC file, then rename or delete the folder where this HOC file lives, then click "Restart".
//    As a result, the app just quits silently.

// !! TODOs:
//  * Maybe update this app to kill the Pyplot subprocs.
//  * Show a clear error message if:
//      * we cannot find "neuron.exe";
//      * user wants to load a Python file, but hoc:nrnpython("") returns 0.
//  * Maybe add a drop-down list to switch between the test entry points.

using System;
using System.Diagnostics;
using System.IO;
using System.Reflection;
using System.Threading;
using System.Windows;
using Microsoft.Win32;

namespace RestartApp
{
    /// <summary>
    /// Interaction logic for MainWindow.xaml
    /// </summary>
    public partial class MainWindow : Window
    {
        private Process LastProc;

        private string LastTempHocFilePathName;

        private string HocOrPyFileName;
        private string HocOrPyDirPath;

        private string NeuronExePath;
        private string MemoryFilePathName;

        private const string MemoryFileName = "last_file_path.txt";

        private const string HocFileExtLower = ".hoc";
        private const string PyFileExtLower = ".py";

        public MainWindow()
        {
            InitializeComponent();

            this.ResizeMode = ResizeMode.NoResize;
            var desktopWorkingArea = SystemParameters.WorkArea;
            this.Left = desktopWorkingArea.Right - this.Width;
            this.Top = desktopWorkingArea.Bottom - this.Height;

            string nrnHome = Environment.GetEnvironmentVariable("NEURONHOME");
            if (nrnHome != null)
            {
                NeuronExePath = Path.Join(nrnHome, @"bin\neuron.exe");
            }
            else
            {
                NeuronExePath = @"C:\nrn\bin\neuron.exe";
            }

            // We use this MemoryFilePathName instead of MemoryFileName everywhere just because
            // the "RestartApp.lnk" relative shortcut file doesn't set up the current working directory
            MemoryFilePathName = Path.Join(Path.GetDirectoryName(Assembly.GetExecutingAssembly().Location), MemoryFileName);

            string lastHocOrPyFilePathName = null;
            if (File.Exists(MemoryFilePathName))
            {
                lastHocOrPyFilePathName = File.ReadAllText(MemoryFilePathName);
            }

            bool isRecalled = (lastHocOrPyFilePathName != null) && File.Exists(lastHocOrPyFilePathName);

            EnableOrDisableButtons(isRecalled);

            HocOrPyFileName = null;
            HocOrPyDirPath = null;
            if (isRecalled)
            {
                ParseHocOrPyFilePathName(lastHocOrPyFilePathName, out HocOrPyFileName, out HocOrPyDirPath);
            }

            UpdateHocOrPyFileNameLabel();
        }

        private void SelectHocOrPyFile_Click(object sender, RoutedEventArgs e)
        {
            var dialog = new OpenFileDialog()
                {
                    Filter = "HOC or Python (*.hoc;*.py)|*.hoc;*.py",
                    FileName = HocOrPyFileName,
                    InitialDirectory = HocOrPyDirPath
                };
            
            bool isSelected = dialog.ShowDialog().Value;

            if (!isSelected)
            {
                return;
            }

            File.WriteAllText(MemoryFilePathName, dialog.FileName);

            EnableOrDisableButtons(isSelected);

            ParseHocOrPyFilePathName(dialog.FileName, out HocOrPyFileName, out HocOrPyDirPath);

            UpdateHocOrPyFileNameLabel();
        }

        private void RestartButton_Click(object sender, RoutedEventArgs e)
        {
            Cleanup();

            string hocFileName;

            string hocOrPyFileNameLower = HocOrPyFileName.ToLower();

            if (hocOrPyFileNameLower.EndsWith(HocFileExtLower))
            {
                hocFileName = HocOrPyFileName;
                LastTempHocFilePathName = null;
            }
            else if (hocOrPyFileNameLower.EndsWith(PyFileExtLower))
            {
                string pyModuleName = HocOrPyFileName[..^PyFileExtLower.Length];

                hocFileName = $"init_{pyModuleName}_temp.hoc";

                string[] lines =
                    {
                        "",
                        "proc sourcePythonCode() { local status",
                        "    strdef pyCommand",
                        "    sprint(pyCommand, \"import sys\\nimport os\\nsys.path.append(os.getcwd() + '%s')\\n%s\", $s1, $s2)",
                        "    status = nrnpython(pyCommand)",
                        "    if (!status) {",
                        "        print \"\\n    Error importing Python code!\"",
                        "    }",
                        "}",
                        "",
                       $"sourcePythonCode(\"\", \"import {pyModuleName}\")"
                    };

                LastTempHocFilePathName = Path.Combine(HocOrPyDirPath, hocFileName);

                File.WriteAllLines(LastTempHocFilePathName, lines);
            }
            else
            {
                throw new System.Exception();
            }

            var procInfo = new ProcessStartInfo(NeuronExePath, hocFileName)
                {
                    WorkingDirectory = HocOrPyDirPath,
                    Verb = "runas"
                };

            LastProc = Process.Start(procInfo);
        }

        private void CloseButton_Click(object sender, RoutedEventArgs e)
        {
            Cleanup();
        }

        private void Window_Closing(object sender, System.ComponentModel.CancelEventArgs e)
        {
            Cleanup();
        }

        private void Cleanup()
        {
            LastProc?.Kill(true);

            if (LastTempHocFilePathName != null)
            {
                for (int attemptIdx = 0; attemptIdx < 10; attemptIdx++)
                {
                    try
                    {
                        File.Delete(LastTempHocFilePathName);
                        break;
                    }
                    catch (IOException)
                    {
                        Thread.Sleep(1000);
                    }
                }
            }
        }

        private void EnableOrDisableButtons(bool isEnabled)
        {
            this.RestartButton.IsEnabled =
                this.CloseButton.IsEnabled = isEnabled;
        }

        private void UpdateHocOrPyFileNameLabel()
        {
            this.HocOrPyFileNameLabel.Content = HocOrPyFileName?.Replace("_", "__");
        }

        private static void ParseHocOrPyFilePathName(string hocFilePathName, out string hocFileName, out string hocDirPath)
        {
            hocFileName = Path.GetFileName(hocFilePathName);
            hocDirPath = Path.GetDirectoryName(hocFilePathName);
        }
    }
}
