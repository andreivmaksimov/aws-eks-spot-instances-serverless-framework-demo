import logging
import os
import subprocess
import shutil

logger = logging.getLogger()
logger.setLevel(logging.INFO)

MY_PATH = os.path.dirname(os.path.realpath(__file__))
ROOT = os.path.abspath(os.path.join(MY_PATH, os.pardir))
DIST_KUBECTL = os.path.join(ROOT, 'bin/kubectl')
DIST_AUTHENTICATOR = os.path.join(ROOT, 'bin/aws-iam-authenticator')
KUBECTL = '/tmp/kubectl'
AUTHENTICATOR = '/tmp/aws-iam-authenticator'
KUBE_CONFIG = os.path.join(ROOT, '.kube/config')

def handler(event, context):

    bucket_name = event['Records'][0]['s3']['bucket']['name']
    file_key = event['Records'][0]['s3']['object']['key']
    logger.info('Reading {} from {}'.format(file_key, bucket_name))

    logger.info('Copying `kubectl` to /tmp to make it executable...')
    shutil.copyfile(DIST_KUBECTL, KUBECTL)
    shutil.copyfile(DIST_AUTHENTICATOR, AUTHENTICATOR)

    logger.info('Making `kubectl` executable...')
    os.chmod(KUBECTL, 0o755)
    logging.info('Now permissions are: {}'.format(oct(os.stat(KUBECTL).st_mode & 0o777)))

    logger.info('Making `aws-iam-authenticator` executable...')
    os.chmod(AUTHENTICATOR, 0o755)
    logging.info('Now permissions are: {}'.format(oct(os.stat(AUTHENTICATOR).st_mode & 0o777)))

    logger.info('Adding /tmp to PATH...')
    os.environ['PATH'] = '{}:/tmp'.format(os.environ['PATH'])

    logger.info('Testing `aws-iam-authenticator`...')
    cmd = 'aws-iam-authenticator token -i aws-eks-spot-serverless-demo-dev'

    logger.info('Execute command: {}'.format(cmd))

    process = subprocess.Popen(
        cmd,
        shell=True,
        cwd='/tmp',
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE
    )

    out, err = process.communicate()
    errcode = process.returncode

    logger.info(
        'Subprocess exited with code: {}. Output: "{}". Error: "{}"'.format(
            errcode, out, err
        )
    )

    job_description = """
apiVersion: batch/v1
kind: Job
metadata:
  name: make-thumbnail
spec:
  template:
    spec:
      containers:
      - name: make-thumbnail
        image: rupakg/docker-ffmpeg-thumb
        env:
          - name: AWS_REGION
            value: us-east-1
          - name: INPUT_VIDEO_FILE_URL
            value: https://s3.amazonaws.com/{}/{}
          - name: OUTPUT_S3_PATH
            value: aws-eks-spot-serverless-demo-dev-thumbnails
          - name: OUTPUT_THUMBS_FILE_NAME
            value: {}
          - name: POSITION_TIME_DURATION
            value: 00:01
      restartPolicy: Never
  backoffLimit: 4

""".format(
    bucket_name,
    file_key,
    '{}.png'.format(file_key.split('.')[0])
)

    cmd = 'kubectl --kubeconfig {} create -f -'.format(KUBE_CONFIG)

    logger.info('Trying to execute command: {}'.format(cmd))

    process = subprocess.Popen(
        cmd,
        shell=True,
        cwd='/tmp',
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE
    )

    out, err = process.communicate(input=job_description.encode())
    errcode = process.returncode

    logger.info(
        'Subprocess exited with code: {}. Output: "{}". Error: "{}"'.format(
            errcode, out, err
        )
    )

    return
