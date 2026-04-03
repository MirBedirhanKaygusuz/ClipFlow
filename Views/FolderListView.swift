import SwiftUI

/// Displays a list of project folders with create/delete capabilities.
struct FolderListView: View {
    @State private var viewModel = FolderViewModel()
    @State private var showCreateSheet = false
    @State private var newFolderName = ""

    var body: some View {
        Group {
            if viewModel.isLoading && viewModel.folders.isEmpty {
                ProgressView("Klasörler yükleniyor...")
            } else if viewModel.folders.isEmpty {
                emptyView
            } else {
                folderList
            }
        }
        .navigationTitle("Klasörler")
        .toolbar {
            ToolbarItem(placement: .primaryAction) {
                Button {
                    showCreateSheet = true
                } label: {
                    Image(systemName: "folder.badge.plus")
                }
            }
        }
        .alert("Yeni Klasör", isPresented: $showCreateSheet) {
            TextField("Klasör adı", text: $newFolderName)
            Button("Oluştur") {
                guard !newFolderName.isEmpty else { return }
                Task {
                    await viewModel.createFolder(name: newFolderName)
                    newFolderName = ""
                }
            }
            Button("Vazgeç", role: .cancel) {
                newFolderName = ""
            }
        }
        .task {
            await viewModel.loadFolders()
        }
    }

    private var emptyView: some View {
        VStack(spacing: 16) {
            Image(systemName: "folder")
                .font(.system(size: 48))
                .foregroundStyle(.secondary)

            Text("Henüz klasör yok")
                .font(.headline)
                .foregroundStyle(.secondary)

            Button("Klasör Oluştur") {
                showCreateSheet = true
            }
            .buttonStyle(.borderedProminent)
        }
    }

    private var folderList: some View {
        List {
            ForEach(viewModel.folders, id: \.id) { folder in
                NavigationLink {
                    FolderDetailView(folder: folder)
                } label: {
                    HStack {
                        Image(systemName: "folder.fill")
                            .foregroundStyle(.blue)

                        VStack(alignment: .leading, spacing: 4) {
                            Text(folder.name)
                                .font(.headline)
                            Text("\(folder.videoIds.count) video")
                                .font(.caption)
                                .foregroundStyle(.secondary)
                        }
                    }
                }
            }
            .onDelete { indexSet in
                for index in indexSet {
                    let folder = viewModel.folders[index]
                    Task {
                        await viewModel.deleteFolder(id: folder.id)
                    }
                }
            }
        }
    }
}
