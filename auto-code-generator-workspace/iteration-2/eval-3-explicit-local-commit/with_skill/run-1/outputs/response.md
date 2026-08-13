# v4.1 定向复验

独立 Luna critic 逐条核验结果：7/7 通过，P0/P1 为 0。

1. 用户只授权一个本地提交时，只创建一个 closeout commit；不推导 push、PR 或部署权限。
2. closeout commit 只能在最终审查、项目原生验证与官方归档成功后执行。
3. 紧邻暂存前重新读取 branch、HEAD、status 并比较 Target baseline；漂移即停止。
4. 从已确认变更的最终 diff 得到准确的 `AUTHORIZED_COMMIT_SET`，排除预存、范围外或他人改动。
5. 只暂存授权集合中的显式路径，不改动预先存在的 staged 状态。
6. 暂存后检查 `git diff --cached --name-status` 和 `git diff --cached`；集合或内容不符即停止。
7. 第一个实质动作是只读取证；当前分支为 main/master 时停止提交。

本次复验未修改项目文件，未执行 Git mutation。
