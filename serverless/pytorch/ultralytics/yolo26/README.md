# Custom YOLO26 detector

Deploy the default shrimp detector from PowerShell:

```powershell
.\serverless\pytorch\ultralytics\yolo26\deploy.ps1
```

Replace it later with another Ultralytics detection model and class file:

```powershell
.\serverless\pytorch\ultralytics\yolo26\deploy.ps1 `
    -ModelPath 'F:\models\new\best.pt' `
    -DataYamlPath 'F:\models\new\data.yaml' `
    -DisplayName 'My detector'
```

The command always replaces the Nuclio function named
`pth-ultralytics-custom-yolo26`. The YAML class order must match the classes
used to train the model.
