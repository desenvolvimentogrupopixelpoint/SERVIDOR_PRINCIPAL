// Seleciona os elementos do modal de adicionar grupo
const addGroupBtn = document.getElementById("add-group-btn");
const addGroupModal = document.getElementById("add-group-modal");
const cancelAddGroupBtn = document.getElementById("cancel-add-group-btn");
const createGroupBtn = document.getElementById("create-group-btn");
const groupNameInput = document.getElementById("group-name");
const groupAddressInput = document.getElementById("group-address");
const groupsTableBody = document.getElementById("groups-table-body");

// Variável para armazenar o grupo sendo editado
let editingGroup = null;

window.addEventListener("load", () => {
  fetch("/get-grupos")
    .then((response) => response.json())
    .then((grupos) => {
      grupos.forEach((grupo) => {
        const newRow = document.createElement("tr");
        newRow.innerHTML = `
          <td>${grupo.nome}</td>
          <td>${grupo.endereco}</td>
          <td>${grupo.status}</td>
          <td>
            <button style="background-color: #007bff; color: white; border: none; padding: 5px 10px; border-radius: 5px; cursor: pointer;" class="edit-group-btn">Editar</button>
            <button style="background-color: #dc3545; color: white; border: none; padding: 5px 10px; border-radius: 5px; cursor: pointer;" class="delete-group-btn">Excluir</button>
            <button style="background-color: #17a2b8; color: white; border: none; padding: 5px 10px; border-radius: 5px; cursor: pointer;" class="view-group-btn">Ver Grupo</button>
          </td>
        `;
        groupsTableBody.appendChild(newRow);
      });
    })
    .catch((error) => console.error("Erro ao carregar grupos:", error));
});


// Abre o modal de adicionar grupo ao clicar no botão "Adicionar Novo Grupo"
addGroupBtn.addEventListener("click", () => {
  addGroupModal.classList.remove("hidden");
  editingGroup = null; // Resetando a variável de grupo em edição
  createGroupBtn.textContent = "Criar";
});

// Fecha o modal de adicionar grupo ao clicar no botão "Cancelar"
cancelAddGroupBtn.addEventListener("click", () => {
  addGroupModal.classList.add("hidden");
});

// Função para criar ou editar um grupo
createGroupBtn.addEventListener("click", () => {
  const groupName = groupNameInput.value.trim();
  const groupAddress = groupAddressInput.value.trim();

  if (groupName && groupAddress) {
    if (editingGroup) {
      // Edição de grupo
      fetch("/editar_grupo", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          nome_antigo: editingGroup.nome,
          novo_nome: groupName,
          novo_endereco: groupAddress,
        }),
      })
        .then((response) => response.json())
        .then((data) => {
          alert(data.message);

          // Atualiza os valores na tabela
          editingGroup.row.cells[0].textContent = groupName;
          editingGroup.row.cells[1].textContent = groupAddress;

          // Limpa os campos e fecha o modal
          groupNameInput.value = "";
          groupAddressInput.value = "";
          addGroupModal.classList.add("hidden");
          editingGroup = null;
          createGroupBtn.textContent = "Criar";
        })
        .catch((error) => console.error("Erro ao editar grupo:", error));
    } else {
      // Criação de grupo
      const novoGrupo = {
        nome: groupName,
        endereco: groupAddress,
        status: "Ativo",
      };

      fetch("/adicionar_grupo", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify(novoGrupo),
      })
        .then((response) => response.json())
        .then((data) => {
          alert(data.message);

          const newRow = document.createElement("tr");
          newRow.innerHTML = `
            <td>${novoGrupo.nome}</td>
            <td>${novoGrupo.endereco}</td>
            <td>${novoGrupo.status}</td>
            <td>
              <button style="background-color: #007bff; color: white; border: none; padding: 5px 10px; border-radius: 5px; cursor: pointer;" class="edit-group-btn">Editar</button>
              <button style="background-color: #dc3545; color: white; border: none; padding: 5px 10px; border-radius: 5px; cursor: pointer;" class="delete-group-btn">Excluir</button>
              <button style="background-color: #17a2b8; color: white; border: none; padding: 5px 10px; border-radius: 5px; cursor: pointer;" class="view-group-btn">Ver Grupo</button>
            </td>
          `;
          groupsTableBody.appendChild(newRow);

          groupNameInput.value = "";
          groupAddressInput.value = "";
          addGroupModal.classList.add("hidden");
        })
        .catch((error) => console.error("Erro ao adicionar grupo:", error));
    }
  } else {
    alert("Por favor, insira o nome e o endereço do grupo.");
  }
});

// Evento para manipular ações na tabela (excluir, editar ou ver grupo)
groupsTableBody.addEventListener("click", (event) => {
  const row = event.target.closest("tr");

  if (event.target.classList.contains("edit-group-btn")) {
    const groupName = row.cells[0].textContent;
    const groupAddress = row.cells[1].textContent;

    groupNameInput.value = groupName;
    groupAddressInput.value = groupAddress;

    addGroupModal.classList.remove("hidden");
    createGroupBtn.textContent = "Salvar";
    editingGroup = { nome: groupName, endereco: groupAddress, row };
  } else if (event.target.classList.contains("delete-group-btn")) {
    const groupName = row.cells[0].textContent;
    document.getElementById("group-name-delete").textContent = groupName;
    document.getElementById("delete-group-modal").classList.remove("hidden");

    const confirmDeleteBtn = document.getElementById("confirm-delete-group-btn");
    const cancelDeleteBtn = document.getElementById("cancel-delete-group-btn");

    const handleConfirmDelete = () => {
      const deletePasswordInput = document.getElementById("delete-password");
      const password = deletePasswordInput.value.trim();

      if (password === "PIPpixelindoor2025") {
        // Se a senha estiver correta, procede com a exclusão
        fetch("/excluir_grupo", {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
          },
          body: JSON.stringify({ nome: groupName }),
        })
          .then((response) => response.json())
          .then((data) => {
            alert(data.message);
            row.remove();
            document
              .getElementById("delete-group-modal")
              .classList.add("hidden");
          })
          .catch((error) => console.error("Erro ao excluir grupo:", error));
      } else {
        // Se a senha estiver incorreta, não faz nada
        deletePasswordInput.value = ""; // Limpa o campo de senha
      }
    };

    const handleCancelDelete = () => {
      // Fecha o modal de exclusão
      document.getElementById("delete-group-modal").classList.add("hidden");

      // Limpa o campo de senha ao cancelar
      const deletePasswordInput = document.getElementById("delete-password");
      deletePasswordInput.value = "";
    };

    // Adiciona eventos ao clicar nos botões
    confirmDeleteBtn.onclick = handleConfirmDelete;
    cancelDeleteBtn.onclick = handleCancelDelete;
  } else if (event.target.classList.contains("view-group-btn")) {
    const groupName = row.cells[0].textContent;

    // Redireciona para a página específica do grupo
    window.location.href = `/grupo/${groupName}`;
  }
});





const confirmDeleteBtn = document.getElementById("confirm-delete-group-btn");
const deletePasswordInput = document.getElementById("delete-password");

confirmDeleteBtn.addEventListener("click", () => {
    const password = deletePasswordInput.value.trim();

    if (password === "PIPpixelindoor2025") {
        // Se a senha estiver correta, procede com a exclusão
        fetch("/excluir_grupo", {
            method: "POST",
            headers: {
                "Content-Type": "application/json",
            },
            body: JSON.stringify({ nome: document.getElementById("group-name-delete").textContent }),
        })
            .then((response) => response.json())
            .then((data) => {
                alert(data.message);
                location.reload(); // Recarrega a página
            })
            .catch((error) => console.error("Erro ao excluir grupo:", error));
    } else {
        // Se a senha estiver incorreta, não faz nada
        deletePasswordInput.value = ""; // Limpa o campo de senha
    }
});



// Evento para abrir o modal de exclusão ao clicar no botão "Excluir"
groupsTableBody.addEventListener("click", (event) => {
    if (event.target.classList.contains("delete-group-btn")) {
        const row = event.target.closest("tr");
        const groupName = row.cells[0].textContent;

        // Atualiza o nome do grupo no modal
        document.getElementById("group-name-delete").textContent = groupName;

        // Exibe o modal de exclusão
        document.getElementById("delete-group-modal").classList.remove("hidden");
    }
});

// Botão "Sim" para confirmar exclusão
document.getElementById("confirm-delete-group-btn").addEventListener("click", () => {
    const password = document.getElementById("delete-password").value.trim();
    const groupName = document.getElementById("group-name-delete").textContent;

    if (password === "PIPpixelindoor2025") {
        // Se a senha estiver correta, realiza a exclusão
        fetch("/excluir_grupo", {
            method: "POST",
            headers: {
                "Content-Type": "application/json",
            },
            body: JSON.stringify({ nome: groupName }),
        })
            .then((response) => response.json())
            .then((data) => {
                alert(data.message);

                // Remove a linha da tabela e fecha o modal
                const rowToDelete = Array.from(groupsTableBody.rows).find(row => row.cells[0].textContent === groupName);
                if (rowToDelete) rowToDelete.remove();
                document.getElementById("delete-group-modal").classList.add("hidden");
            })
            .catch((error) => console.error("Erro ao excluir grupo:", error));
    } else {
        // Exibe mensagem de erro se a senha estiver incorreta
        document.getElementById("delete-password").value = ""; // Limpa o campo de senha
    }
});

// Botão "Cancelar" para fechar o modal de exclusão
document.getElementById("cancel-delete-group-btn").addEventListener("click", () => {
    document.getElementById("delete-group-modal").classList.add("hidden");
    document.getElementById("delete-password").value = ""; // Limpa o campo de senha ao cancelar
});


