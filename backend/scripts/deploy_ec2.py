"""Launch the Amacide API on EC2.

The account denies IAM, so the instance can't have a role; it gets the workshop's
temporary credentials instead. Both the code and the credentials are fetched from
presigned S3 URLs that expire in 15 minutes, so no secret is ever written into
user-data itself (user-data is readable by anything on the box via IMDS).
"""
import io, tarfile, time
from pathlib import Path
import boto3

REGION, BUCKET = "us-east-1", "amacide-985539753760"
AMI, SUBNET, SG = "ami-0b2c9d1f3edcfd709", "subnet-022a425d5e9899def", "sg-00f031e6a00c2d93b"
BACKEND = Path("/home/stefan/Documents/Backup/GitHub/hackathon_aws/backend")

s3 = boto3.client("s3", region_name=REGION)
ec2 = boto3.client("ec2", region_name=REGION)

# ---- package the app ----
buf = io.BytesIO()
with tarfile.open(fileobj=buf, mode="w:gz") as tar:
    for sub in ("src", "scripts"):
        tar.add(BACKEND / sub, arcname=sub,
                filter=lambda ti: None if "__pycache__" in ti.name else ti)
s3.put_object(Bucket=BUCKET, Key="deploy/app.tgz", Body=buf.getvalue())
print(f"app.tgz: {len(buf.getvalue())} bytes")

# ---- credentials (never printed) ----
s3.put_object(Bucket=BUCKET, Key="deploy/creds", Body=Path.home().joinpath(".aws/credentials").read_bytes())

presign = lambda key: s3.generate_presigned_url("get_object", Params={"Bucket": BUCKET, "Key": key}, ExpiresIn=900)
app_url, creds_url = presign("deploy/app.tgz"), presign("deploy/creds")

USER_DATA = f"""#!/bin/bash
set -xe
exec > /var/log/amacide-setup.log 2>&1
dnf install -y python3-pip
pip3 install --quiet boto3
mkdir -p /opt/amacide /root/.aws
curl -fsS "{app_url}" -o /tmp/app.tgz
tar xzf /tmp/app.tgz -C /opt/amacide
curl -fsS "{creds_url}" -o /root/.aws/credentials
chmod 600 /root/.aws/credentials
cat > /etc/systemd/system/amacide.service <<'UNIT'
[Unit]
Description=Amacide game API
After=network-online.target
[Service]
Environment=HOME=/root
ExecStart=/usr/bin/python3 -u /opt/amacide/scripts/serve_local.py --port 8000
Restart=always
RestartSec=3
[Install]
WantedBy=multi-user.target
UNIT
systemctl daemon-reload
systemctl enable --now amacide
echo SETUP_DONE
"""

r = ec2.run_instances(
    ImageId=AMI, InstanceType="t3.micro", MinCount=1, MaxCount=1,
    SubnetId=SUBNET, SecurityGroupIds=[SG], UserData=USER_DATA,
    MetadataOptions={"HttpTokens": "required"},            # IMDSv2 only
    TagSpecifications=[{"ResourceType": "instance",
                        "Tags": [{"Key": "Name", "Value": "amacide-api"}]}],
)
iid = r["Instances"][0]["InstanceId"]
print("instance:", iid)

ec2.get_waiter("instance_running").wait(InstanceIds=[iid])
desc = ec2.describe_instances(InstanceIds=[iid])["Reservations"][0]["Instances"][0]
ip = desc.get("PublicIpAddress")
print("public ip:", ip)
print("state:", desc["State"]["Name"])
Path("/tmp/claude-1000/-home-stefan-Documents-Backup-GitHub-hackathon-aws/d63ad03e-058e-41f8-ba68-152d81efe082/scratchpad/ec2.env").write_text(f"IID={iid}\nIP={ip}\n")
