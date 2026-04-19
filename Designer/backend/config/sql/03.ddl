-- 03.ddl: K8S 多副本运维观测字段
-- 给 t_workflow_run 加 worker_id + heartbeat_at,方便排查"哪个 pod 在跑"和"卡住多久"。
-- 幂等通过 t_migration_applied 的 checksum 守护(MySQL 8 不支持 ADD COLUMN IF NOT EXISTS)。

ALTER TABLE t_workflow_run
  ADD COLUMN worker_id    VARCHAR(128) NULL,
  ADD COLUMN heartbeat_at DATETIME(6)  NULL;

CREATE INDEX ix_wr_worker_heartbeat
  ON t_workflow_run (worker_id, heartbeat_at);
