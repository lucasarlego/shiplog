# Abre o Shiplog em modo app (Edge/Chrome) e garante a janela maximizada.
# Com o navegador já aberto, ele ignora --start-maximized; por isso a janela nova é maximizada aqui.
param([string]$Url = "http://127.0.0.1:8765", [string]$Titulo = "Shiplog")

Add-Type @"
using System; using System.Text; using System.Collections.Generic; using System.Runtime.InteropServices;
public class ShiplogJanela {
  delegate bool P(IntPtr h, IntPtr l);
  [DllImport("user32.dll")] static extern bool EnumWindows(P p, IntPtr l);
  [DllImport("user32.dll")] static extern int GetWindowText(IntPtr h, StringBuilder s, int n);
  [DllImport("user32.dll")] static extern bool IsWindowVisible(IntPtr h);
  [DllImport("user32.dll")] public static extern bool ShowWindow(IntPtr h, int c);
  [DllImport("user32.dll")] public static extern bool SetForegroundWindow(IntPtr h);
  public static List<IntPtr> Com(string t) {
    var r = new List<IntPtr>();
    EnumWindows((h, l) => { if (IsWindowVisible(h)) { var s = new StringBuilder(256); GetWindowText(h, s, 256); if (s.ToString() == t) r.Add(h); } return true; }, IntPtr.Zero);
    return r;
  }
}
"@

$antes = [ShiplogJanela]::Com($Titulo)
$args_ = @("--app=$Url", "--start-maximized")
try { Start-Process msedge -ArgumentList $args_ -WindowStyle Maximized -ErrorAction Stop }
catch {
  try { Start-Process chrome -ArgumentList $args_ -WindowStyle Maximized -ErrorAction Stop }
  catch { Start-Process $Url; exit 0 }
}

# Espera a janela nova (o título vem do <title> da página) e maximiza.
for ($i = 0; $i -lt 50; $i++) {
  Start-Sleep -Milliseconds 200
  $nova = [ShiplogJanela]::Com($Titulo) | Where-Object { $antes -notcontains $_ } | Select-Object -First 1
  if ($nova) {
    [void][ShiplogJanela]::ShowWindow($nova, 3)   # SW_MAXIMIZE
    [void][ShiplogJanela]::SetForegroundWindow($nova)
    exit 0
  }
}
