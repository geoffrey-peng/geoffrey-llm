"""Dot-accessible provider and region constants.

Values are plain strings, so they are fully interchangeable with hand-written
``provider`` / ``region`` strings and accepted everywhere ``CloudConfig``
fields are used. The constants exist so callers never need to hand-type
vendor identifiers or region IDs::

    from geoffrey_llm.cloud import CloudClient, CloudConfig, Provider, Region

    client = CloudClient(CloudConfig(
        provider=Provider.ALIBABA,
        region=Region.ALIBABA.CN_BEIJING,
    ))
"""


class Provider:
    """云厂商标识，作为 ``CloudConfig.provider`` 的取值。"""

    ALIBABA = "alibaba"
    TENCENT = "tencent"
    HUAWEI = "huawei"
    AWS = "aws"
    MOCK = "mock"

    ALL = (ALIBABA, TENCENT, HUAWEI, AWS, MOCK)


class _AlibabaRegion:
    """阿里云地域（ECS/VPC/RDS/OSS 通用 region id）。"""

    CN_BEIJING = "cn-beijing"            # 华北2（北京）
    CN_ZHANGJIAKOU = "cn-zhangjiakou"    # 华北3（张家口）
    CN_HUHEHAOTE = "cn-huhehaote"        # 华北5（呼和浩特）
    CN_WULANCHABU = "cn-wulanchabu"      # 华北6（乌兰察布）
    CN_HANGZHOU = "cn-hangzhou"          # 华东1（杭州）
    CN_SHANGHAI = "cn-shanghai"          # 华东2（上海）
    CN_SHENZHEN = "cn-shenzhen"          # 华南1（深圳）
    CN_HEYUAN = "cn-heyuan"              # 华南2（河源）
    CN_GUANGZHOU = "cn-guangzhou"        # 华南3（广州）
    CN_CHENGDU = "cn-chengdu"            # 西南1（成都）
    CN_HONGKONG = "cn-hongkong"          # 中国香港
    AP_SOUTHEAST_1 = "ap-southeast-1"    # 新加坡
    AP_SOUTHEAST_5 = "ap-southeast-5"    # 雅加达
    AP_NORTHEAST_1 = "ap-northeast-1"    # 东京
    US_EAST_1 = "us-east-1"              # 弗吉尼亚
    US_WEST_1 = "us-west-1"              # 硅谷
    EU_CENTRAL_1 = "eu-central-1"        # 法兰克福


class _TencentRegion:
    """腾讯云地域（CVM/VPC/CDB/COS 通用 region id）。"""

    AP_GUANGZHOU = "ap-guangzhou"        # 广州
    AP_BEIJING = "ap-beijing"            # 北京
    AP_SHANGHAI = "ap-shanghai"          # 上海
    AP_NANJING = "ap-nanjing"            # 南京
    AP_CHENGDU = "ap-chengdu"            # 成都
    AP_CHONGQING = "ap-chongqing"        # 重庆
    AP_HONGKONG = "ap-hongkong"          # 中国香港
    AP_SINGAPORE = "ap-singapore"        # 新加坡
    AP_TOKYO = "ap-tokyo"                # 东京
    AP_SEOUL = "ap-seoul"                # 首尔
    NA_SILICONVALLEY = "na-siliconvalley"  # 硅谷
    NA_ASHBURN = "na-ashburn"            # 弗吉尼亚
    EU_FRANKFURT = "eu-frankfurt"        # 法兰克福


class _HuaweiRegion:
    """华为云地域（ECS/VPC/RDS/OBS 通用 region id）。"""

    CN_NORTH_1 = "cn-north-1"            # 华北一（北京）
    CN_NORTH_4 = "cn-north-4"            # 华北四（北京）
    CN_NORTH_9 = "cn-north-9"            # 华北九（北京）
    CN_EAST_2 = "cn-east-2"              # 华东二（上海）
    CN_EAST_3 = "cn-east-3"              # 华东三（上海）
    CN_SOUTH_1 = "cn-south-1"            # 华南一（广州）
    CN_SOUTHWEST_2 = "cn-southwest-2"    # 西南二（贵阳）
    AP_SOUTHEAST_1 = "ap-southeast-1"    # 中国香港
    AP_SOUTHEAST_3 = "ap-southeast-3"    # 新加坡
    AP_NORTHEAST_1 = "ap-northeast-1"    # 东京


class _AwsRegion:
    """AWS 地域（EC2/S3/RDS 通用 region id）。"""

    US_EAST_1 = "us-east-1"              # 弗吉尼亚
    US_EAST_2 = "us-east-2"              # 俄亥俄
    US_WEST_1 = "us-west-1"              # 北加利福尼亚
    US_WEST_2 = "us-west-2"              # 俄勒冈
    CA_CENTRAL_1 = "ca-central-1"        # 加拿大中部
    EU_WEST_1 = "eu-west-1"              # 爱尔兰
    EU_CENTRAL_1 = "eu-central-1"        # 法兰克福
    AP_NORTHEAST_1 = "ap-northeast-1"    # 东京
    AP_NORTHEAST_2 = "ap-northeast-2"    # 首尔
    AP_SOUTHEAST_1 = "ap-southeast-1"    # 新加坡
    AP_SOUTHEAST_2 = "ap-southeast-2"    # 悉尼
    AP_SOUTH_1 = "ap-south-1"            # 孟买
    SA_EAST_1 = "sa-east-1"              # 圣保罗


class Region:
    """云地域常量，按厂商分组，作为 ``CloudConfig.region`` 的取值。"""

    ALIBABA = _AlibabaRegion
    TENCENT = _TencentRegion
    HUAWEI = _HuaweiRegion
    AWS = _AwsRegion
