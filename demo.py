from datetime import datetime, timedelta

import requests
import json


class CodingAPI:

    def __init__(self):
        self.url = "https://e.coding.net/open-api/?action=DescribeIssueList"
        self.token = "Bearer 47d4d7eb8e622a85c58485246946bd71236d93bc"
        self.webhook_url = "https://qyapi.weixin.qq.com/cgi-bin/webhook/send?key=8bbee69d-31ae-435f-89b6-f14a6b629776"
        self.issues_url = "https://g-homv8048.coding.net/p/minguangxitong/bug-tracking/issues/"

    def get_current_time(self):
        """获取当前时间的年月日和时间"""
        now = datetime.now()
        return now.strftime("%Y-%m-%d %H:%M:%S")

    def get_date_offset(self, days: int):
        """获取当前时间前后指定天数的日期"""
        target_date = datetime.now() + timedelta(days=days)
        return target_date.strftime("%Y-%m-%d")
    # 获取上周的开始时间和结束时间
    def get_last_week_dates(self, last_week_nums=1):
        """
        获取上周的开始日期（周一）和结束日期（周日）
            last_week_nums 指定是几周前
        返回:
            tuple: (start_date, end_date) 格式为datetime.date对象
        """
        if type(last_week_nums) != int:
            last_week_nums = 1
            print("输入参数的数据类型错误，默认使用上周时间")
        today = datetime.now().date()
        # 计算今天是本周的第几天（周一为0，周日为6）
        weekday = today.weekday()
        # 计算上周一的日期
        start_date = today - timedelta(days=weekday + 7*last_week_nums)
        # 计算上周日的日期
        end_date = start_date + timedelta(days=6)

        return start_date, end_date

    # 团队成员列表查询
    def get_team_members(self):
        """获取团队成员列表"""
        url = "https://e.coding.net/open-api/?action=DescribeTeamMembers"
        headers = {
            'Content-Type': 'application/json',
            'Accept': 'application/json',
            'Authorization': self.token
        }
        payload = json.dumps({
            "PageNumber": 1,
            "PageSize": 10
        })
        response = requests.request("POST", url, headers=headers, data=payload)
        action_data_json = json.loads(response.text)
        # 提取 "IssueList" 中的 "Name" 字段
        issue_list = action_data_json["Response"]["Data"]["TeamMembers"]
        extracted_data = [
            {
                "Id": issue["Id"],
                "Name": issue["Name"],
            }
            for issue in issue_list
        ]
        return {item['Name']: item['Id'] for item in extracted_data}

    # 获取项目列表
    def get_action_list(self, IssueType="DEFECT", start_date=None, end_date=None):
        """
        :param IssueType:事项类型
            ALL - 全部事项
            DEFECT - 缺陷
            REQUIREMENT - 需求
            MISSION - 任务
            EPIC - 史诗
        :param start_date: 开始日期，格式为 "YYYY-MM-DD"
        :param end_date: 结束日期，格式为 "YYYY-MM-DD"
        :return:
        """
        payload = json.dumps({
            "ProjectName": "minguangxitong",
            "IssueType": IssueType,
            "Offset": "0",
            "Limit": "10",
            "Conditions": [  # 将 conditions 转换为 JSON 字符串
                # {
                #     "Key": "ASSIGNEE",
                #     "Value": "9238399",    # 处理人ID
                # },
                # {
                #     "Key": "CREATOR",
                #     "Value": "9238388", # 创建人ID
                # },
                {
                    "Key": "CREATED_AT",
                    "Value": f"{start_date}_{end_date}", # 创建时间
                }
            ],
                "SortKey": "CODE",
                "SortValue": "DESC"
            })
        headers = {
            'Content-Type': 'application/json',
            'Accept': 'application/json',
            'Authorization': self.token
        }
        response = requests.request("POST", self.url, headers=headers, data=payload)
        return response.json()

    def deal_action_data(self):
        action_data_json = json.loads(self.get_action_list())
        # 提取 "IssueList" 中的 "Name" 字段
        issue_list = action_data_json["Response"]["IssueList"]
        extracted_data = [
            {
                "Code":issue["Code"],
                "Name": issue["Name"],
                "IssueStatusName": issue["IssueStatusName"],
                "Description": issue["Description"],
                "AssigneeId": issue["AssigneeId"]
            }
            for issue in issue_list
        ]
        for item in extracted_data:
            print(item)
        return extracted_data

    def process_coding_data(self, json_data, project_url="https://g-homv8048.coding.net/p/minguangxitong/bug-tracking"):
        """
        处理Coding缺陷数据并结构化输出
        :param json_data: Coding API返回的原始JSON数据
        :param project_url: 项目主页地址（用于生成缺陷链接）
        :return: 结构化后的缺陷列表
        """
        processed_issues = []

        # 优先级映射表（根据Coding平台定义调整）
        priority_map = {
            "1": "🔥紧急",
            "2": "⚠️高",
            "3": "⚡中",
            "4": "🌿低"
        }

        for issue in json_data.get("Response", {}).get("IssueList", []):
            # 基础字段提取
            issue_code = issue.get("Code")
            assignees = [u["Name"] for u in issue.get("Assignees", []) if u.get("Id") == issue.get("AssigneeId")]

            # 时间处理（Coding的时间戳为毫秒级）
            created_at = datetime.fromtimestamp(issue.get("CreatedAt", 0) / 1000)
            days_pending = (datetime.now() - created_at).days

            # 构建缺陷对象
            processed = {
                "id": issue_code,
                "link": f"{project_url}/issues/{issue_code}",
                "title": issue.get("Name", "无标题缺陷"),
                "priority": priority_map.get(issue.get("Priority", "4")),
                "assignee": assignees[0] if assignees else "未分配",
                "status": issue.get("IssueStatusName", "未知状态"),
                "days_pending": days_pending,
                "last_updated": datetime.fromtimestamp(issue.get("UpdatedAt", 0) / 1000).strftime("%Y-%m-%d %H:%M"),
                "blocker": self.extract_blocker(issue)
            }
            processed_issues.append(processed)

        return processed_issues

    def extract_blocker(self, issue):
        """
        提取阻塞原因（根据实际业务规则扩展）
        """
        # 示例逻辑：从描述或自定义字段提取
        if issue.get("Description", "").strip():
            return issue["Description"]

        # 可扩展解析特定格式的阻塞标记，例如：
        # if "blocker" in issue.get("Labels", []):
        #     return "优先级阻塞"

        return "待补充"

    def send_to_wechat(self, content):
        webhook_url = self.webhook_url

        """将处理后的数据转换为企业微信Markdown格式"""
        lines = [
            "**🚨 每周缺陷战报 | {}**\n".format(datetime.now().strftime("%Y-%m-%d")),
            "------------------------"
        ]

        for issue in content:
            lines.append(
                f"`{issue['priority']}` [{issue['id']} {issue['title']}]({issue['link']})\n"
                f"▸ 负责人：@{issue['assignee']} | 滞留：{issue['days_pending']}天\n"
                f"▸ 最后更新：{issue['last_updated']}\n"
                # f"▸ 阻塞原因：{issue['blocker']}\n"
                "------------------------"
            )
        data = {
                "msgtype": "markdown",
                "markdown": {
                    "content": "\n".join(lines)
                }
            }
        requests.post(webhook_url, json=data)
        return "\n".join(lines)

    def main(self):
        # 获取团队成员
        team_members = self.get_team_members()

        all_issues = []
        for member_name, member_id in team_members.items():
            last_week_start, last_week_end = self.get_last_week_dates(last_week_nums=1)
            # 获取指定时间内的缺陷列表
            data = self.get_action_list(start_date=last_week_start, end_date=last_week_end)
            processed_data = self.process_coding_data(data)

            # 过滤出当前成员的缺陷
            member_issues = [issue for issue in processed_data if issue['assignee'] == member_name]
            all_issues.extend(member_issues)
        print(all_issues)
        # 发送到企业微信
        self.send_to_wechat(all_issues)
    def test(self):
        last_week_start, last_week_end = self.get_last_week_dates(last_week_nums=0)
        print(f"上周开始日期: {last_week_start}")
        print(f"上周结束日期: {last_week_end}")
if __name__ == '__main__':
    coding = CodingAPI()
    coding.main()

