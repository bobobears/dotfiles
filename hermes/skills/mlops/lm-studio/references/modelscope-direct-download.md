# ModelScope 直链下载 + aria2c 陷阱（2026-08-15 验证）

## ModelScope 直链下载（国内最快，无需镜像）

发现量化文件后（见 `modelscope-model-discovery.md`），直接下载：

```bash
cd ~/.lmstudio/models/lmstudio-community/<Model>-GGUF/
aria2c -x 8 -s 8 --continue=true \
  --user-agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36" \
  -o "<filename>.gguf" \
  "https://www.modelscope.cn/models/<owner>/<repo>/resolve/master/<filename>.gguf"
```

- URL 模式：`https://www.modelscope.cn/models/{owner}/{repo}/resolve/master/{file}`
- 302 重定向到 `cdn-lfs-cn-1.modelscope.cn`（国内 CDN），8 线程实测 6-11 MiB/s
- 多模态模型同一目录还需要 `mmproj-*.gguf`（如 `mmproj-BF16.gguf`）

## ⚠️ aria2c `-A` 陷阱（本次实际踩坑）

**`-A` 是 `--allow-overwrite` 的简写，不是 User-Agent！**

```bash
# ❌ 错误：报 "无效的选项 -- A" / exit 28
aria2c -A "Mozilla/5.0" <url>

# ✅ 正确：用 --user-agent 或 --header
aria2c --user-agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36" <url>
aria2c --header="User-Agent: huggingface-hub/1.21.0" <url>   # hf-mirror 方式也有效
```

`-A` 后面跟任意字符串都会报 `aria2c: 无效的选项 -- A`（OptionParser errorCode=28），因为 bash 把 `-A "Mozilla/5.0"` 解析成 `--allow-overwrite=Mozilla/5.0` 之类。排查时看到 exit 28 + "invalid option" 先怀疑短选项简写冲突。

## 下载完成验证三步

1. **大小核对**：文件大小 == ModelScope API `Size` 字段（如 Q8_0 29.05GB → 29,047,085,024 字节）
2. **无残留**：`ls *.aria2` 无输出（有 `.aria2` 控制文件 = aria2c 未 finalize）
3. **GGUF 文件头**：
```python
import struct
with open('<file>.gguf', 'rb') as f:
    magic = f.read(4)
    version = struct.unpack('<I', f.read(4))[0]
    n_tensors = struct.unpack('<Q', f.read(8))[0]
    n_kv = struct.unpack('<Q', f.read(8))[0]
print(magic, version, n_tensors, n_kv)  # b'GGUF' 3 866 51 之类
```

## 实测案例：Qwen3.8-27B-Q8_0

- `unsloth/Qwen3.8-27B-GGUF` 的 Q8_0 直链：29.05 GB，8 线程 ~10 MiB/s，全程约 43 分钟
- mmproj-BF16.gguf 888 MiB 单独任务，~5 MiB/s 约 3 分钟
- 下载到 `~/.lmstudio/models/lmstudio-community/Qwen3.8-27B-GGUF/`，LM Studio 刷新即可识别
- GB10 显存注意：加载 29GB 模型前若 ComfyUI 占 36GB、free 仅 11GB，需要先停 ComfyUI
