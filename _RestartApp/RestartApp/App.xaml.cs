using System.Threading;
using System.Windows;

namespace RestartApp
{
    /// <summary>
    /// Interaction logic for App.xaml
    /// </summary>
    public partial class App : Application
    {
        private static Mutex mutex;

        protected override void OnStartup(StartupEventArgs e)
        {
            bool isNewInstance;
            mutex = new Mutex(true, "RestartApp", out isNewInstance);

            if (!isNewInstance)
            {
                MessageBox.Show("Another instance of RestartApp is already running.", "RestartApp", MessageBoxButton.OK, MessageBoxImage.Warning);
                Application.Current.Shutdown();
            }
            else
            {
                base.OnStartup(e);
            }
        }

        protected override void OnExit(ExitEventArgs e)
        {
            mutex?.ReleaseMutex();
            base.OnExit(e);
        }
    }
}
