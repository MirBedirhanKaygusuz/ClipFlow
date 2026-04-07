import SwiftUI

@main
struct ClipFlowApp: App {
    var body: some Scene {
        WindowGroup {
            TabView {
                HomeView()
                    .tabItem {
                        Label("Düzenle", systemImage: "scissors")
                    }
                
                FolderListView()
                    .tabItem {
                        Label("Projeler", systemImage: "folder")
                    }
            }
            .preferredColorScheme(.dark)
            .tint(Theme.neonTeal)
        }
    }
}
