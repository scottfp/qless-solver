FROM python:3.12-slim

# Install system dependencies
RUN apt-get update && apt-get install -y \
    git \
    curl \
    build-essential \
    gnupg \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Install GitHub CLI
RUN curl -fsSL https://cli.github.com/packages/githubcli-archive-keyring.gpg | dd of=/usr/share/keyrings/githubcli-archive-keyring.gpg \
    && chmod go+r /usr/share/keyrings/githubcli-archive-keyring.gpg \
    && echo "deb [arch=$(dpkg --print-architecture) signed-by=/usr/share/keyrings/githubcli-archive-keyring.gpg] https://cli.github.com/packages stable main" | tee /etc/apt/sources.list.d/github-cli.list > /dev/null \
    && apt-get update \
    && apt-get install -y gh \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Set up non-root user
ARG USERNAME=vscode
ARG USER_UID=1000
ARG USER_GID=$USER_UID

RUN groupadd --gid $USER_GID $USERNAME \
    && useradd --uid $USER_UID --gid $USER_GID -m $USERNAME \
    && apt-get update \
    && apt-get install -y sudo \
    && echo $USERNAME ALL=\(root\) NOPASSWD:ALL > /etc/sudoers.d/$USERNAME \
    && chmod 0440 /etc/sudoers.d/$USERNAME

# Add ~/.local/bin to PATH for the vscode user
RUN echo 'export PATH=$PATH:$HOME/.local/bin' >> /home/$USERNAME/.bashrc

# Install pip tools and pre-commit
RUN pip install --no-cache-dir --upgrade pip setuptools wheel pre-commit

# Set up a working directory
WORKDIR /workspace

# Switch to the vscode user
USER $USERNAME

# Install uv for the vscode user
RUN curl -LsSf https://astral.sh/uv/install.sh | sh

# Add the vscode user's cargo bin to PATH
RUN echo 'export PATH=$PATH:$HOME/.cargo/bin' >> /home/$USERNAME/.bashrc
