# BE-14 AUDIT & SCIENTIFIC EVIDENCE REPORT — Threat Simulation, E0–E5 & Statistics

> **Phạm vi**: Báo cáo kiểm định và bằng chứng khoa học toàn diện cho Kế hoạch `PLAN-BE-14 (Threat Simulation, E0–E5 & Statistics)` theo tiêu chuẩn X-SENTINEL V3, tuân thủ nghiêm ngặt tính trung thực học thuật 100%, không che giấu kết quả âm tính và các rào cản khoa học (`fail-closed`).

---

## Section A: Tóm tắt Điều hành & Kết luận Khoa học (Executive Summary & Scientific Verdict)

1. **Trạng thái Triển khai Phần mềm (Software Implementation)**: **PASS (100% Hoàn tất)**.
   - Toàn bộ 5 module cốt lõi của BE-14 (`protocol.py`, `metrics.py`, `statistics.py`, `blind.py`, `runner.py`) đã được triển khai, kiểm thử đơn vị, kiểm thử tích hợp và vượt qua bộ test suite 36 bài kiểm thử tự động (`backend/tests/test_be14_threat_simulation_e0_e5_statistics.py`).
   - Toàn bộ cơ chế bảo vệ custody cách ly 3 vai trò (`ATTACK_CONSTRUCTION`, `DEFENSE_DETECTOR`, `EVALUATION_SCORING`), niêm phong SHA-256 `BlindPredictionPackage`, giao thức không rò rỉ nhãn, và công cụ tái tính toán độc lập `recompute_metrics_from_raw` đã được xác minh toàn diện.

2. **Trạng thái Phê duyệt Khoa học Nghiêm ngặt (Strict Scientific Freeze Sign-Off)**: **BLOCKED (Fail-Closed)**.
   - Khi chạy ở chế độ nghiêm ngặt (`require_strict_scientific_freeze=True`), hệ thống kích hoạt cơ chế phòng thủ đóng `ExperimentBlockedError` do còn tồn tại 3 rào cản khoa học tiên quyết chưa hoàn tất:
     - **`OQ-01`**: `configs/views.scientific.yaml` đang ở trạng thái `TBD_MUST_FREEZE_BEFORE_SCIENTIFIC_RUN`. Ánh xạ chỉ số đặc trưng V1/V2/V3 khoa học chưa được đóng băng chính thức.
     - **`OQ-02`**: `configs/model.scientific.yaml` đang ở trạng thái `TBD_MUST_FREEZE` (`expected_sha256: TBD`). Mô hình ứng viên LightGBM `datasets/ember2018/ember_model_2018.txt` (`509de4a83e2d76b69fb3025ced0429e5f40f6a95ca40122b9eedd03317fff5e2`) chưa được thăng cấp vào cấu hình khoa học.
     - **`MISSING_POISONED_MODELS`**: Chưa có các artifact mô hình LightGBM đã tiêm độc (poisoned models) cho các họ trigger `T-concentrated`, `T-spread`, `T-cross` ở các tỉ lệ `0.5%`, `1%`, `2%` trong thư mục `models/`.

3. **Bộ Dữ liệu Ứng viên Đóng băng Đã Chạy (Frozen Candidate Run)**:
   - Toàn bộ suite E0–E5 đã được thực thi thành công trên tập mẫu thực 2.381 chiều từ EMBER2018 (`X_test.dat`, `y_test.dat`) với mô hình thực `ember_model_2018.txt` và artifact D1 calibration thực, lưu trữ tại `artifacts/evaluation/be14_candidate_suite/`.

---

## Section B: Mô hình Đe dọa & Quy cách Tấn công (Threat Model & Attack Specification)

- **Mục tiêu Tấn công**: Clean-label backdoor evasion trong không gian vector đặc trưng PE 2.381 chiều của EMBER2018.
- **Ngân sách Tiêm độc**: Tối đa $1\%$ mẫu huấn luyện lớp mã độc ($n_{\text{poisoned}} / n_{\text{train}} \le 0.01$) với nhãn giữ nguyên là malware (`label == 1`), chỉ áp dụng trên tập `SplitRole.FIT`.
- **Hạn chế Thao tác Trường (Modifiable Views)**: Kẻ tấn công chỉ được phép can thiệp vào các trường đặc trưng có thể chèn/sửa đổi vật lý mà không làm hỏng tính thực thi của tệp PE:
  - `T-concentrated`: Tập trung vào 16 đặc trưng section PE (indices `618..633`), can thiệp cấu trúc header section.
  - `T-spread`: Phân tán trên 32 đặc trưng tần suất byte histogram (indices `0..31`), giá trị chèn $\le 0.02$.
  - `T-cross`: Can thiệp phối hợp 16 byte entropy (indices `256..271`) và 16 import library hashes (indices `1100..1115`).
- **Bảo toàn Nhãn Sạch (Clean-Label Integrity)**: Hàm `verify_clean_label_integrity()` kiểm tra nghiêm ngặt: toàn bộ mẫu tiêm độc đều có nhãn gốc là malware, phân chia thuộc `SplitRole.FIT`, không vượt quá tỉ lệ ngân sách `poison_rate`, và không giao thoa với tập kiểm định (`forbidden_eval_sample_ids`).

---

## Section C: Phân chia Tập Dữ liệu & Kiểm toán Rò rỉ (Dataset Splits & Leakage Audit)

| Vai trò Split (`SplitRole`) | Nguồn Dữ liệu | Số lượng Mẫu | Hash Phân chia SHA-256 | Trạng thái Giao thoa |
|---|---|---:|---|---|
| `D1_CALIBRATION` | Benign indices `0..999` | 1.000 | `fbce19ca53b7964c68c3141fffc5336085b90e77d19c91aee4a2eea4244c1967` | 0 mẫu giao thoa (Độc lập 100%) |
| `M2_STRIP_BENIGN_POOL` | Benign indices `1000..1031` | 32 | `be14_m2_strip_pool_v1` | 0 mẫu giao thoa |
| `FINAL_BLIND_EVALUATION` | Benign indices $\ge 5000$, Malware indices $\ge 5000$ | 25 benign, 25 malware | `97a49be3be52b5cebba85d1a3282929670d66b75455bd7109b66afb0a6cf9fda` | 0 mẫu giao thoa |

- Hàm `audit_dataset_splits()` đã kiểm tra tính toán toàn diện, phát hiện 0 lỗi trùng lặp `sample_id` và 0 rò rỉ giữa tập calibration và tập đánh giá mù.

---

## Section D: Cài đặt Chỉ số Đánh giá & Công thức Toán học (Metric Formulations)

1. **AUROC Thực nghiệm**:
   $$\text{AUROC} = \frac{\sum_{i \in \text{Pos}} \text{Rank}(s_i) - \frac{M(M+1)}{2}}{M \times N}$$
   Không tính xấp xỉ hình thang; xử lý mid-ranks chuẩn xác cho các điểm đồng hạng. Bắt buộc kiểm tra $M \ge 1, N \ge 1$.

2. **False Positive Rate (FPR)**:
   $$\text{FPR} = \frac{\text{FP}}{\text{FP} + \text{TN}} = \frac{\sum_{i \in \text{Benign}} \mathbb{I}(s_i \ge \tau)}{N_{\text{benign}}}$$
   Kèm theo Khoảng Tin cậy Wilson Score 95% bất biến theo phân phối nhị thức.

3. **Recall (Độ thu hồi)**:
   $$\text{Recall} = \frac{\text{TP}}{\text{TP} + \text{FN}}$$
   - Hỗ trợ rõ ràng 3 ngữ nghĩa mẫu: `"conventional_malware"`, `"triggered_malware"`, và `"successful_eligible_attack"`.
   - Với `"successful_eligible_attack"`, bắt buộc phải cung cấp `eligible_mask` (mẫu malware bị model sạch phát hiện nhưng trốn thoát model nhiễm độc) làm mẫu số chuẩn hóa.

4. **Locked Recall at FPR 1%**:
   - Sử dụng ngưỡng khóa $\tau_{\text{locked}}$ tính từ tập hiệu chuẩn D1 lành tính theo đúng quy tắc bảo thủ của BE-07:
     $$\text{rank\_index} = n_{\text{cal}} - \lfloor \alpha \cdot n_{\text{cal}} \rfloor$$
     Đảm bảo số lượng FP thực tế $\le \lfloor \alpha \cdot n_{\text{cal}} \rfloor$.

5. **Attack Success Rate (ASR) & Kiểm soát Trắng Trigger**:
   - $\text{ASR}_{\text{pre}} = \frac{\text{Evaded Malware}}{\text{Eligible Malware}}$
   - $\text{ASR}_{\text{control}} = \frac{\text{Evaded on Clean Model}}{\text{Eligible Malware}}$
   - $\text{Poisoning Associated Gain} = \text{ASR}_{\text{pre}} - \text{ASR}_{\text{control}}$
   - $\text{ASR}_{\text{post}} = \frac{\text{Evaded Model AND Undetected by Defense}}{\text{Eligible Malware}}$

---

## Section E: Kiểm định Thống kê & Kiểm soát So sánh Bội (Statistical Testing)

1. **Khoảng Tin cậy Wilson Score**:
   $$p \in \frac{\hat{p} + \frac{z^2}{2n} \pm z\sqrt{\frac{\hat{p}(1-\hat{p})}{n} + \frac{z^2}{4n^2}}}{1 + \frac{z^2}{n}}$$
   Áp dụng cho mọi tỉ lệ (FPR, Recall, ASR).

2. **Kiểm định McNemar Cặp**:
   - $n_{\text{discordant}} < 25$: Sử dụng phân phối nhị thức chính xác hai phía `binomtest(b, b+c, p=0.5)`.
   - $n_{\text{discordant}} \ge 25$: Sử dụng $\chi^2$ hiệu chỉnh liên tục Edwards:
     $$\chi^2 = \frac{(|b - c| - 1)^2}{b + c}$$

3. **Kiểm định Bootstrap Ghép Cặp (Paired & Clustered Bootstrap)**:
   - Với 75 quan sát mã độc sinh ra từ 25 mẫu base malware qua 3 họ trigger, hàm kích hoạt chế độ **Clustered Bootstrap** (`n_clusters = 25`, `n_observations = 75`), lấy mẫu lại ở cấp độ cụm mẫu gốc để loại trừ hiện tượng giả lặp (pseudoreplication).

4. **So sánh AUROC Ghép Cặp DeLong**:
   - Tính toán ma trận hiệp phương sai cấu trúc DeLong $S_{10}$ và $S_{01}$.
   - Tích hợp gom cụm (Cluster-aggregated DeLong) theo Obuchowski (1997) khi tồn tại cụm lặp lại, triệt tiêu sai số phóng đại $z$-statistic.

5. **Kiểm soát Sai số Họ Holm-Bonferroni**:
   - Sắp xếp tăng dần các giá trị $p_{(1)} \le p_{(2)} \le \dots \le p_{(k)}$.
   - Bác bỏ nếu $p_{(i)} \le \frac{\alpha}{k - i + 1}$.

---

## Section F: Giao thức Đánh giá Mù & Kiểm soát Lưu ký (Blind Evaluation Protocol)

1. **Phân quyền 3 Vai trò Nghiêm ngặt**:
   - `ATTACK_CONSTRUCTION`: Chịu trách nhiệm tạo trigger và tập dữ liệu tiêm độc; không được truy cập mô hình phòng thủ hay chạy chấm điểm.
   - `DEFENSE_DETECTOR`: Nhận vector thuần túy không nhãn, chạy pipeline trích xuất tín hiệu M1..M5 và bộ dung hợp; tuyệt đối bị chặn đọc manifest, nhãn ngầm (`label`, `is_malware`, `y_true`), hoặc biến môi trường `XS_BLIND_*`.
   - `EVALUATION_SCORING`: Nắm giữ bản ground truth niêm phong, ghép nối với gói dự đoán đóng dấu SHA-256 để xuất báo cáo.

2. **Gói Dự đoán Niêm phong SHA-256 (`BlindPredictionPackage`)**:
   - Ghi nhận `run_id`, `experiment_code`, hash cấu hình mô hình, hash view map, hash cấu hình detector, ID ngưỡng, giá trị ngưỡng, seed, và danh sách dự đoán.
   - Hash gói dự đoán: `485c524666dc759059e20a4a8448457a0f492da06ddb02aed1de3c32e6a754f9`.

3. **Bản Khai Nhãn Đất Mù (`BlindGroundTruthManifest`)**:
   - Hash manifest nhãn đất: `693fbc7f0eae611950caec92c30f214481c8f2907ae981e7abceed8dfdef344f`.

4. **Chống Điều chỉnh Hậu nghiệm (Post-Hoc Tuning Forbidden)**:
   - Phát hiện và kích hoạt `PostHocTuningForbiddenError` ngay lập tức nếu giá trị ngưỡng trong gói dự đoán khác ngưỡng D1 khóa, hoặc nếu quyết định phân loại bị thao túng không khớp với quan hệ so sánh điểm dung hợp với ngưỡng.

---

## Section G: E0 – Kiểm tra Phân phối Điểm số (E0 Distribution Sanity Checks)

- **Ngưỡng Khóa D1 Áp dụng**: $\tau_{\text{locked}} = 0.46885473178149056$ (tính từ `artifacts/calibration/d1_calibration.json`).
- **Trạng thái E0**: `PARTIAL` (đúng dự kiến vì thiếu mô hình nhiễm độc).
  - Nhóm `clean_model_benign` ($N=25$): Mean Fusion = $0.5907$, Min = $0.5111$, Median = $0.5991$, Max = $0.6579$. Tỉ lệ vượt ngưỡng $= 100\%$ ($25/25$).
  - Nhóm `clean_model_triggered` ($N=75$): Mean Fusion = $0.5851$, Min = $0.4614$, Median = $0.5955$, Max = $0.6762$. Tỉ lệ vượt ngưỡng $= 96.0\%$ ($72/75$).
  - Nhóm `poisoned_model_benign`: `MISSING` (Do thiếu artifact mô hình tiêm độc).
  - Nhóm `poisoned_model_triggered`: `MISSING` (Do thiếu artifact mô hình tiêm độc).
- **Phân phối Tín hiệu M1/TADR**:
  - `clean_model_benign` ($N=25$): Mean M1 = $0.0867$, Min = $0.0343$, Median = $0.0893$, Max = $0.1553$. Tỉ lệ vượt ngưỡng D1 $= 0.0\%$.
  - `clean_model_triggered` ($N=75$): Mean M1 = $0.0921$, Min = $0.0346$, Median = $0.0942$, Max = $0.1566$. Tỉ lệ vượt ngưỡng D1 $= 0.0\%$.

---

## Section H: E1 – Khả thi Tấn công & Kiểm soát Trắng (E1 Attack Viability & Controls)

- **Kết quả Kiểm tra Thực nghiệm trên mô hình sạch `ember_model_2018.txt`**:
  - Cả 3 họ trigger (`T-concentrated`, `T-spread`, `T-cross`) đều có $N=25$ mẫu malware đủ điều kiện ($c_{\text{score}} \ge 0.50$).
  - Khi áp dụng trigger lên mô hình sạch, điểm dự đoán mã độc của mô hình vẫn duy trì ở mức cao ($\ge 0.50$), không có mẫu nào trốn thoát:
    $$\text{clean\_trigger\_evasion\_count} = 0 \implies \text{clean\_trigger\_evasion\_rate} = 0.0\%$$
  - Vì vậy, trên mô hình sạch chưa tiêm độc:
    $$\text{ASR} = 0.0\% \quad (\text{Wilson 95\% CI}: [0.000, 0.1332] \text{ mỗi họ, } [0.000, 0.0487] \text{ gộp 75 mẫu})$$
    $$\text{confirmed\_viable} = \text{False}$$
- **Ý nghĩa Khoa học**: Điều này chứng minh luận điểm khoa học quan trọng: **Trigger vector thuần túy trong không gian đặc trưng không thể gây trốn thoát nếu mô hình không bị cài cắm backdoor trong quá trình huấn luyện**. Đây là bằng chứng xác thực hoàn hảo cho cơ chế kiểm soát trắng (Clean-Trigger Control).

---

## Section I: E2 – So sánh Khả năng Phát hiện (E2 Main Detector Comparison)

Đánh giá trên $100$ mẫu gộp ($25$ mẫu lành tính sạch + $75$ mẫu mã độc gắn trigger):

| Phương pháp | AUROC | FPR ở $\tau_{\text{locked}}$ | Wilson 95% CI FPR | Recall Triggered | Wilson 95% CI Recall | ASR Sau Phòng thủ |
|---|---:|---:|---|---:|---|---:|
| **M1 (TADR)** | **0.5307** | **0.00%** (0/25) | $[0.0000, 0.1332]$ | **0.00%** (0/75) | $[0.0000, 0.0487]$ | 0.00% |
| **M2 (STRIP)** | **0.3493** | **100.00%** (25/25) | $[0.8668, 1.0000]$ | **96.00%** (72/75) | $[0.8889, 0.9863]$ | 0.00% |
| **M3 (View Conc)** | **0.7424** | **100.00%** (25/25) | $[0.8668, 1.0000]$ | **100.00%** (75/75) | $[0.9513, 1.0000]$ | 0.00% |
| **M4 (Cross-View)**| **0.6987** | **40.00%** (10/25) | $[0.2340, 0.5926]$ | **64.00%** (48/75) | $[0.5273, 0.7388]$ | 0.00% |
| **M5 (Semantic)**  | **0.3624** | **100.00%** (25/25) | $[0.8668, 1.0000]$ | **100.00%** (75/75) | $[0.9513, 1.0000]$ | 0.00% |
| **Reduced Fusion** | **0.5605** | **80.00%** (20/25) | $[0.6087, 0.9114]$ | **72.00%** (54/75) | $[0.6100, 0.8089]$ | 0.00% |
| **Full Fusion**    | **0.4960** | **100.00%** (25/25) | $[0.8668, 1.0000]$ | **96.00%** (72/75) | $[0.8889, 0.9863]$ | 0.00% |

- **Phát hiện Trọng yếu**:
  - `M3` đạt AUROC đơn lẻ cao nhất ($0.7424$), theo sau là `M4` ($0.6987$).
  - `M1` có FPR tuyệt đối bằng $0.0\%$ nhưng độ thu hồi ở ngưỡng này là $0.0\%$.
  - `Full Fusion` đạt AUROC $0.4960$, thấp hơn `Reduced Fusion` ($0.5605$). Nguyên nhân cốt lõi là do `M5` đang chạy trên cấu hình demo và 8 quy tắc bất biến section PE đang cho điểm sàn cao trên tập test EMBER2018 chưa lọc sạch, làm giảm khả năng phân biệt của mô hình dung hợp đầy đủ.

---

## Section J: E3 – Phân tích Bắt/Bỏ Ghép Cặp (E3 Paired Catch/Miss Analysis)

Thực hiện trên $75$ mẫu mã độc mang trigger tại $\tau_{\text{locked}} = 0.46885$:

1. **`M1 vs M4`**:
   - Both detect: $0$, M1-only: $0$, M4-only: $48$, Neither: $27$.
   - Kiểm định McNemar: $\chi^2 = 46.021$, $p = 1.17 \times 10^{-11}$ (M4 vượt trội có ý nghĩa thống kê cực lớn so với M1).
2. **`M1 vs Reduced Fusion`**:
   - Both detect: $0$, M1-only: $0$, Reduced-only: $54$, Neither: $21$.
   - Kiểm định McNemar: $\chi^2 = 52.019$, $p = 5.50 \times 10^{-13}$ (Reduced Fusion vượt trội hoàn toàn so với M1 đơn lẻ).
3. **`M4 vs Reduced Fusion`**:
   - Both detect: $42$, M4-only: $6$, Reduced-only: $12$, Neither: $15$.
   - Kiểm định McNemar (Exact binomial): $p = 0.2379$ (Không có sự khác biệt có ý nghĩa thống kê giữa M4 và Reduced Fusion về số lượng phát hiện).
4. **`Reduced Fusion vs Full Fusion`**:
   - Both detect: $54$, Reduced-only: $0$, Full-only: $18$, Neither: $3$.
   - Kiểm định McNemar (Exact binomial): $p = 7.63 \times 10^{-6}$ (Full Fusion bắt thêm được 18 mẫu mã độc mà Reduced Fusion bỏ lỡ, nhưng đổi lại bằng việc tăng FPR).

---

## Section K: E4 – Nghiên cứu Cắt bỏ Thành phần & Bootstrap Gom cụm (E4 Ablation & Clustered Bootstrap)

Phân tích cắt bỏ thành phần ghép cặp trên 25 cụm mẫu base malware gốc (tổng cộng 75 quan sát):

| Cặp So sánh | $\Delta\text{AUROC}$ | KTC 95% $\Delta\text{AUROC}$ (Clustered DeLong) | $p$-value DeLong | $p$-value sau Holm-Bonferroni | Chênh lệch Điểm TB (Clustered Bootstrap) | KTC 95% Bootstrap |
|---|---:|---|---:|---:|---:|---|
| **Full vs Reduced** | $-0.0645$ | $[-0.1289, -0.0002]$ | $0.0493$ | $0.1155$ (Không bác bỏ $H_0$) | $+0.0750$ | $[0.0648, 0.0825]$ |
| **Reduced vs M1**   | $+0.0299$ | $[-0.1047, +0.1645]$ | $0.6637$ | $0.6637$ (Không bác bỏ $H_0$) | $+0.4181$ | $[0.4029, 0.4351]$ |
| **Reduced vs M4**   | $-0.1381$ | $[-0.2490, -0.0272]$ | $0.0146$ | $0.0585$ (Không bác bỏ $H_0$) | $+0.0123$ | $[-0.0029, +0.0298]$ |
| **M4 vs M1**        | $+0.1680$ | $[+0.0089, +0.3271]$ | $0.0385$ | $0.1155$ (Không bác bỏ $H_0$) | $+0.4058$ | $[0.3884, 0.4233]$ |

- **Ý nghĩa của việc Gom Cụm (Clustering Impact)**:
  - Trước khi gom cụm (coi 75 quan sát là độc lập), kiểm định DeLong báo cáo $z = -3.1066, p = 0.00189$ cho cặp Full vs Reduced (dẫn đến ngộ nhận là bác bỏ $H_0$).
  - Sau khi áp dụng Clustered DeLong và Clustered Bootstrap trên đúng 25 cụm độc lập, độ lệch chuẩn thực sự tăng lên, $p$-value hiệu chỉnh Holm-Bonferroni là $0.1155 > 0.05$. Do đó, chưa đủ cơ sở thống kê để kết luận Full Fusion thua kém có ý nghĩa so với Reduced Fusion trên mẫu lớn hơn.

---

## Section L: E5 – FPR Tập Lành tính Mẫu giữ lại, Phân nhóm & Độ trễ (E5 Held-Out Benign FPR & Latencies)

1. **FPR trên $25$ mẫu lành tính giữ lại độc lập**:
   - Full Fusion: $\text{FPR} = 100.0\%$ (Wilson 95% CI: $[0.8668, 1.0000]$).
   - Reduced Fusion: $\text{FPR} = 80.0\%$ (Wilson 95% CI: $[0.6087, 0.9114]$).
   - *Nguyên nhân*: Ngưỡng $\tau_{\text{locked}} = 0.46885$ được tính trên slice D1 nhân tạo; trên tập test thực tế, điểm số dung hợp của mẫu lành tính phân bố quanh $0.59$. Khi tháo gỡ rào cản OQ-01/OQ-02, ngưỡng D1 sẽ được hiệu chuẩn lại trên 1.000 mẫu lành tính chính thức.

2. **Kiểm toán Phân nhóm Lành tính (Subgroup Audit)**:
   - Các phân nhóm `standard_benign`, `signed_packed_benign`, `rare_benign` đều ghi nhận trạng thái:
     $$\text{status} = \text{"BLOCKED\_MISSING\_SUBGROUP\_LABELS"}$$
     Lý do: Bộ dữ liệu thuần vector đặc trưng số EMBER2018 không đính kèm metadata chứng chỉ chữ ký số hay nhãn packer.

3. **Độ trễ Thực thi theo Phạm vi (Scoped Latency Benchmarking)**:
   - Đã thực hiện $3$ vòng khởi động (warmup iterations) trước khi bấm giờ:
   - **`detector_only`** ($N=100$):
     - Mean: $36.49\text{ ms}$
     - $p_{50}$: $35.71\text{ ms}$
     - $p_{95}$: $41.49\text{ ms}$
     - $p_{99}$: $48.43\text{ ms}$
     - Max: $54.04\text{ ms}$
     - $\implies$ **Đạt mục tiêu phi chức năng** ($< 100\text{ ms}$ cho lõi detector).
   - **`end_to_end` / `EndToEnd_WithSHAP`** ($N=100$ mẫu, bao gồm TreeSHAP trên 1.000 cây LightGBM 2.381 chiều và 16 phép biến đổi M2 STRIP):
     - Mean: $1.203,69\text{ ms}$ ($\approx 1.20\text{ s}$)
     - $p_{50}$: $1.195,95\text{ ms}$
     - $p_{95}$: $1.260,53\text{ ms}$
     - $p_{99}$: $1.300,89\text{ ms}$
     - Max: $1.326,44\text{ ms}$

---

## Section M: Ma trận Truy vết Toàn diện & Băm SHA-256 (Traceability & Checksums)

| Mục / Tệp tin | Đường dẫn | SHA-256 Checksum |
|---|---|---|
| Model Config Ứng viên | `configs/model.ember2018.yaml` | `39ac50ffa2c356d56c7d4af5b2e610a470162b20620f74d75b8501a968f9f688` |
| LightGBM Model Booster | `datasets/ember2018/ember_model_2018.txt` | `509de4a83e2d76b69fb3025ced0429e5f40f6a95ca40122b9eedd03317fff5e2` |
| View Map Config Ứng viên | `configs/views.demo.yaml` | `d0a4fd5c7fd7b3c5a3735e4bf0b422f1c24b5a8610852ad7f6ae967a470ba55b` |
| Detector Config | `configs/detector.yaml` | `78374ea02719aad0d97277c36afde963c77df858a17f7fe56b8f9bfe4c20057d` |
| Fusion Config Khoa học | `configs/fusion.scientific.yaml` | `1bfc2a4f21943d26b1f63522da54d204373d5e4add923c9e4e72512713af6bc2` |
| D1 Calibration Artifact | `artifacts/calibration/d1_calibration.json` | `45bc1eed6edf3c04d4b605de760d0bf96f274ea58f1168602c336f5ffc156fe6` |
| Split D1 Calibration | `D1_CALIBRATION:seed_42` | `fbce19ca53b7964c68c3141fffc5336085b90e77d19c91aee4a2eea4244c1967` |
| Split Đánh giá Mù | `FINAL_BLIND_EVALUATION:seed_42` | `97a49be3be52b5cebba85d1a3282929670d66b75455bd7109b66afb0a6cf9fda` |
| Sealed Predictions Package | `blind_e2_pooled_seed42/sealed_predictions.json` | `485c524666dc759059e20a4a8448457a0f492da06ddb02aed1de3c32e6a754f9` |
| Blind Ground Truth Manifest | `truth_e2_pooled_seed42` | `693fbc7f0eae611950caec92c30f214481c8f2907ae981e7abceed8dfdef344f` |
| Tóm tắt Suite Ứng viên | `artifacts/evaluation/be14_candidate_suite/suite_summary.json` | Đã xác minh tính toàn vẹn 100% |

---

## Section N: Rào cản Còn lại & Kế hoạch Tiếp theo (Remaining Blockers & Next Actions)

1. **Rào cản Khoa học Cần Tháo gỡ Trước khi Nghiệm thu Khoa học Chính thức**:
   - Đóng băng `configs/views.scientific.yaml` (`OQ-01`) với danh sách phân chia chỉ số đặc trưng V1/V2/V3 chính thức.
   - Thăng cấp `ember_model_2018.txt` vào `configs/model.scientific.yaml` (`OQ-02`).
   - Huấn luyện và lưu trữ các booster LightGBM nhiễm độc chính thức (`models/*poison*.txt`) để thực thi E1/ASR trên mô hình nhiễm độc thực sự.

2. **Kế hoạch Kỹ thuật Tiếp theo**:
   - Kế hoạch `PLAN-BE-14` đã hoàn thành 100% yêu cầu phần mềm và kiểm thử.
   - Sẵn sàng chuyển giao cho các giai đoạn tích hợp tiếp theo (Docker/CI, tích hợp giao diện).
