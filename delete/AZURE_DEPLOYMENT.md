# AstroGen Azure Container Apps (ACA) GPU Deployment Guide

This guide walks you through deploying the AstroGen FastAPI backend to **Azure Container Apps (ACA)** with GPU support. Because you have an Azure Student/Free subscription, we'll use the CLI and Portal steps compatible with your tier.

---

## 🛠️ Step 1: Install Prerequisites (On your PC)
1. **Docker Desktop**: Install [Docker Desktop](https://www.docker.com/products/docker-desktop/) (ensure it is running).
2. **Azure CLI**: Install the [Azure CLI](https://docs.microsoft.com/en-us/cli/azure/install-azure-cli).

---

## 🔑 Step 2: Login to Azure via CLI
Open your terminal (PowerShell or Command Prompt) and login to your Azure Student account:
```bash
az login
```
*A browser tab will open. Sign in using your student email/credentials.*

---

## 📦 Step 3: Create Resource Group & Container Registry (ACR)
An Azure Container Registry (ACR) is where we will upload your Docker image.

1. **Create a Resource Group** (e.g., in East US):
   ```bash
   az group create --name AstroGenRG --location eastus
   ```

2. **Create a Container Registry (Basic SKU)**:
   ```bash
   az acr create --resource-group AstroGenRG --name astrogenregistry --sku Basic --admin-enabled true
   ```
   *Note: Registry name must be globally unique and alphanumeric only.*

3. **Login to your ACR**:
   ```bash
   az acr login --name astrogenregistry
   ```

---

## 🐳 Step 4: Build & Push the Docker Image
1. Open terminal at the root of the `AstroGen` project.
2. Build the Docker image locally:
   ```bash
   docker build -t astrogenregistry.azurecr.io/astrogen-backend:latest -f backend/Dockerfile backend
   ```
3. Push the image to Azure:
   ```bash
   docker push astrogenregistry.azurecr.io/astrogen-backend:latest
   ```

---

## 🚀 Step 5: Deploy to Azure Container Apps (ACA)
1. Register the Azure Container Apps CLI extension:
   ```bash
   az extension add --name containerapp --upgrade
   ```

2. Register the namespace providers:
   ```bash
   az provider register --namespace Microsoft.App
   az provider register --namespace Microsoft.OperationalInsights
   ```

3. Create the Container App Environment:
   ```bash
   az containerapp env create --name AstroGenEnv --resource-group AstroGenRG --location eastus
   ```

4. Deploy the Container App with GPU:
   ```bash
   az containerapp create \
     --name astrogen-api \
     --resource-group AstroGenRG \
     --environment AstroGenEnv \
     --image astrogenregistry.azurecr.io/astrogen-backend:latest \
     --target-port 8000 \
     --ingress external \
     --min-replicas 0 \
     --max-replicas 1 \
     --secrets hf-token="your_hf_token_here",gemini-key="your_gemini_key_here" \
     --env-vars HF_API_TOKEN=secretref:hf-token GEMINI_API_KEY=secretref:gemini-key \
     --registry-server astrogenregistry.azurecr.io
   ```
   *Replace `your_hf_token_here` and `your_gemini_key_here` with your actual Hugging Face and Gemini API keys.*

5. **Enable GPU support**:
   If the student tier allows GPU allocation in your region, you can scale the container profiles to include a GPU (e.g., `NVIDIA-T4`) in the Azure Portal under your Container App settings -> **Containers** -> **CPU/Memory/GPU**. 
   *Note: If your subscription/region has GPU restrictions, it will automatically run on the fast CPU fallback since our code handles it.*

---

## 🌐 Step 6: Connect your Desktop App to the Cloud
Once deployed, the `az containerapp create` command will output a public URL (e.g., `https://astrogen-api.happyhill-12345.eastus.azurecontainerapps.io`).

1. Open your frontend config or PyQt6 launcher.
2. Change the API endpoint URL from `http://localhost:8001` to your new Azure URL!
