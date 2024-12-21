import torch
import torch.nn as nn
import torchvision.models as models

# Load ResNet-18 without pretrained weights
model = models.resnet18(pretrained=False)
model.fc = nn.Linear(model.fc.in_features, 100)  # Modify the final layer for 100 classes (CIFAR-100)

device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
model = model.to(device)



import torch
import torch.nn as nn
import torch.optim as optim
import torchvision.transforms as transforms
import torchvision.datasets as datasets
from torch.utils.data import DataLoader
from torch.optim.lr_scheduler import CyclicLR
from torch.cuda.amp import GradScaler, autocast

# Hyperparameters
batch_size = 128
learning_rate = 0.001
num_epochs = 10
early_stop_patience = 3

# Data Augmentation
transform = transforms.Compose([
    transforms.RandomCrop(32, padding=4),
    transforms.RandomHorizontalFlip(),
    transforms.ColorJitter(brightness=0.2, contrast=0.2, saturation=0.2, hue=0.2),
    transforms.ToTensor(),
    transforms.Normalize((0.5, 0.5, 0.5), (0.5, 0.5, 0.5)),
])

# Load CIFAR-100 dataset
trainset = datasets.CIFAR100(root='./data', train=True, download=True, transform=transform)
trainloader = DataLoader(trainset, batch_size=batch_size, shuffle=True, num_workers=2)

testset = datasets.CIFAR100(root='./data', train=False, download=True, transform=transform)
testloader = DataLoader(testset, batch_size=batch_size, shuffle=False, num_workers=2)

# model = EfficientNetLiteCNN().to(device)
criterion = nn.CrossEntropyLoss()
optimizer = optim.Adam(model.parameters(), lr=learning_rate)
scheduler = CyclicLR(optimizer, base_lr=0.0001, max_lr=0.01, step_size_up=2000)
scaler = GradScaler()  # Mixed precision

# Early stopping and checkpointing
best_val_acc = 0.0
early_stop_counter = 0

# Training and validation loop with early stopping
for epoch in range(num_epochs):
    model.train()
    running_loss = 0.0
    for inputs, labels in trainloader:
        inputs, labels = inputs.to(device), labels.to(device)

        optimizer.zero_grad()

        with autocast():  # Mixed precision
            outputs = model(inputs)
            loss = criterion(outputs, labels)

        scaler.scale(loss).backward()
        scaler.step(optimizer)
        scaler.update()
        running_loss += loss.item()

    scheduler.step()

    print(f'Epoch {epoch + 1}/{num_epochs}, Loss: {running_loss/len(trainloader)}')

    # Validation loop for early stopping
    model.eval()
    correct = 0
    total = 0
    with torch.no_grad():
        for inputs, labels in testloader:
            inputs, labels = inputs.to(device), labels.to(device)
            outputs = model(inputs)
            _, predicted = torch.max(outputs.data, 1)
            total += labels.size(0)
            correct += (predicted == labels).sum().item()

    val_acc = 100 * correct / total
    print(f'Validation Accuracy: {val_acc:.2f}%')

    # Early stopping check
    if val_acc > best_val_acc:
        best_val_acc = val_acc
        early_stop_counter = 0
        torch.save(model.state_dict(), 'best_model_effnet.pth')  # Save checkpoint
    else:
        early_stop_counter += 1
        if early_stop_counter >= early_stop_patience:
            print("Early stopping triggered.")
            break

# Load the best model
model.load_state_dict(torch.load('best_model_effnet.pth'))

# Test loop
model.eval()
correct = 0
total = 0
with torch.no_grad():
    for inputs, labels in testloader:
        inputs, labels = inputs.to(device), labels.to(device)
        outputs = model(inputs)
        _, predicted = torch.max(outputs.data, 1)
        total += labels.size(0)
        correct += (predicted == labels).sum().item()

print(f'Test Accuracy: {100 * correct / total:.2f}%')
