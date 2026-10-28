# Quy tắc tài nguyên (RAM, CPU, kết nối, luồng)

Áp dụng cho cả tích hợp Home Assistant (`custom_components/tritue_youtube_player`) và add-on máy chủ (`youtube_player/app`).
Tích hợp chạy trong tiến trình Home Assistant dùng chung: một chỗ ngốn tài nguyên là cả Home Assistant đầy RAM rồi bị khởi động lại.

1. **Hàng đợi, bộ nhớ đệm, danh sách luôn có trần.** Mọi hàng đợi có `maxsize`; bộ nhớ đệm có trần số mục VÀ hạn dùng
   (`app/gioi_han.cat_bo_nho_dem`); thừa thì bỏ mục cũ/sắp hết hạn trước.
2. **Không chặn vòng lặp sự kiện** (tích hợp): không `time.sleep`, `requests`, `subprocess.run` trong mã bất đồng bộ; việc nặng
   đi qua `hass.async_add_executor_job`; dùng phiên HTTP chung `async_get_clientsession`, không tự tạo `ClientSession`.
3. **Việc nặng có trần chạy cùng lúc** (add-on): trích xuất `yt-dlp` và tìm kiếm đi qua `gioi_han.chiem_cho`, hết chỗ thì xếp
   hàng có hạn rồi báo bận, không mở thêm tiến trình/luồng vô hạn.
4. **Mở nhanh, đóng nhanh.** Kết nối ra ngoài mở khi cần, đóng ngay khi xong, đóng trong `finally`; không giữ kết nối rảnh.
5. **Lỗi lặp thì nghỉ tăng dần**; mọi vòng `while True` có `await` thật; tác vụ nền tạo bằng `async_create_background_task` và
   huỷ khi gỡ; mỗi loa/phiên chỉ một tác vụ (ví dụ `dong_bo`: lệnh phát mới huỷ tác vụ cũ).
6. **Nhật ký chỉ ghi kiểu lỗi một lần**, không ghi mỗi vòng, không ghi nội dung bí mật.
