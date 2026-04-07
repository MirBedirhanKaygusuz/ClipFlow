import SwiftUI

/// Main screen for viewing and managing project folders.
struct FolderListView: View {
    @State private var viewModel = FolderViewModel()
    @State private var searchText = ""

    var filteredFolders: [Folder] {
        if searchText.isEmpty {
            return viewModel.folders
        } else {
            return viewModel.folders.filter { $0.name.localizedCaseInsensitiveContains(searchText) }
        }
    }

    var body: some View {
        NavigationStack {
            ZStack {
                Theme.background.ignoresSafeArea()

                Group {
                    if viewModel.isLoading {
                        ProgressView("Klasörler yükleniyor...")
                            .controlSize(.large)
                            .tint(Theme.neonTeal)
                            .foregroundStyle(.white)
                    } else if viewModel.folders.isEmpty {
                        emptyStateView
                    } else {
                        listView
                    }
                }
                .padding(.top)
            }
            .navigationTitle("Projeler")
            .navigationBarTitleDisplayMode(.large)
            .toolbarColorScheme(.dark, for: .navigationBar)
            .toolbarBackground(Theme.background, for: .navigationBar)
            .toolbarBackground(.visible, for: .navigationBar)
            .searchable(text: $searchText, prompt: "Klasör Ara")
            .toolbar {
                ToolbarItem(placement: .topBarTrailing) {
                    Button {
                        viewModel.showingCreateAlert = true
                    } label: {
                        Image(systemName: "folder.badge.plus")
                            .font(.title3)
                            .foregroundStyle(Theme.neonTeal)
                    }
                }
            }
            .task {
                await viewModel.loadFolders()
            }
            .refreshable {
                await viewModel.loadFolders()
            }
            .alert("Hata", isPresented: Binding(
                get: { viewModel.error != nil },
                set: { if !$0 { viewModel.error = nil } }
            )) {
                Button("Tamam", role: .cancel) { }
            } message: {
                Text(viewModel.error ?? "Bilinmeyen bir hata oluştu.")
            }
            .alert("Yeni Klasör", isPresented: $viewModel.showingCreateAlert) {
                TextField("Klasör Adı", text: $viewModel.newFolderName)
                Button("İptal", role: .cancel) {
                    viewModel.newFolderName = ""
                }
                Button("Oluştur") {
                    Task { await viewModel.createFolder() }
                }
            }
            .alert("Yeniden Adlandır", isPresented: Binding(
                get: { viewModel.folderToRename != nil },
                set: { if !$0 { viewModel.folderToRename = nil } }
            )) {
                TextField("Yeni Ad", text: $viewModel.renamedFolderName)
                Button("İptal", role: .cancel) {
                    viewModel.renamedFolderName = ""
                }
                Button("Kaydet") {
                    if let folder = viewModel.folderToRename {
                        Task { await viewModel.renameFolder(folder) }
                    }
                }
            }
        }
    }

    // MARK: - Subviews

    private var emptyStateView: some View {
        VStack(spacing: 20) {
            Image(systemName: "folder")
                .font(.system(size: 64))
                .foregroundStyle(Theme.textSecondary)

            Text("Henüz proje yok")
                .font(.title2.bold())
                .foregroundStyle(.white)

            Text("Videolarını düzenlemek için yeni bir klasör oluştur.")
                .font(.subheadline)
                .foregroundStyle(Theme.textSecondary)
                .multilineTextAlignment(.center)
                .padding(.horizontal)

            Button {
                viewModel.showingCreateAlert = true
            } label: {
                Label("Yeni Klasör Oluştur", systemImage: "plus")
            }
            .buttonStyle(NeonBorderButtonStyle())
            .padding(.horizontal, 40)
            .padding(.top, 10)
        }
    }

    private var listView: some View {
        ScrollView {
            LazyVStack(spacing: 16) {
                ForEach(filteredFolders) { folder in
                    folderRow(folder)
                        .contextMenu {
                            Button {
                                viewModel.folderToRename = folder
                                viewModel.renamedFolderName = folder.name
                            } label: {
                                Label("Yeniden Adlandır", systemImage: "pencil")
                            }

                            Button(role: .destructive) {
                                Task { await viewModel.deleteFolder(folder) }
                            } label: {
                                Label("Sil", systemImage: "trash")
                            }
                        }
                }
            }
            .padding(.horizontal)
        }
    }

    private func folderRow(_ folder: Folder) -> some View {
        GlassyCard {
            HStack(spacing: 16) {
                ZStack {
                    Circle()
                        .fill(Theme.neonTeal.opacity(0.15))
                        .frame(width: 48, height: 48)
                    Image(systemName: "folder.fill")
                        .font(.system(size: 24))
                        .foregroundStyle(Theme.neonTeal)
                }

                VStack(alignment: .leading, spacing: 4) {
                    Text(folder.name)
                        .font(.headline)
                        .foregroundStyle(.white)

                    Text("\(folder.videoIds.count) video • \(folder.createdAt.formatted(date: .abbreviated, time: .shortened))")
                        .font(.caption)
                        .foregroundStyle(Theme.textSecondary)
                }

                Spacer()

                Image(systemName: "chevron.right")
                    .font(.subheadline)
                    .foregroundStyle(.secondary)
            }
        }
    }
}

#Preview {
    FolderListView()
}
