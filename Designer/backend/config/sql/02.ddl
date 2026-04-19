-- 02.ddl: Run event log(ChatFlow spec 派生)— 支持 resume 与 audit。
-- 所有 `RunEvent` 在广播到 Redis 之前必须先入此表;前端 resume 时按 `id` 增量读取。

CREATE TABLE IF NOT EXISTS t_run_event_log (
  id            BIGINT AUTO_INCREMENT PRIMARY KEY,
  run_id        VARCHAR(32)  NOT NULL,
  message_id    VARCHAR(32)  NULL,
  event_type    VARCHAR(64)  NOT NULL,
  event_data    JSON         NOT NULL,
  created_at    DATETIME(6)  NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
  INDEX ix_rel_run_id (run_id, id),
  INDEX ix_rel_run_msg (run_id, message_id, id),
  INDEX ix_rel_created (created_at),
  CONSTRAINT chk_rel_event_type CHECK (CHAR_LENGTH(event_type) > 0)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
