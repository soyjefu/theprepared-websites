<?php
/* Servers configuration */
$i = 0;

/* Server: MariaDB [1] */
$i++;
$cfg['Servers'][$i]['host'] = 'mariadb_db'; // docker-compose.yml의 MariaDB 서비스 이름
$cfg['Servers'][$i]['port'] = '3306';
$cfg['Servers'][$i]['socket'] = '';
$cfg['Servers'][$i]['connect_type'] = 'tcp';
$cfg['Servers'][$i]['compress'] = false;
$cfg['Servers'][$i]['auth_type'] = 'cookie'; //쿠키 인증 방식 / phpMyAdmin에 접속하면 아이디와 비밀번호를 입력하는 로그인 페이지가 나타나. 로그인 정보는 암호화된 쿠키를 통해 세션 동안 유지돼. 
// $cfg['Servers'][$i]['user'] = getenv('MARIADB_USER'); // .env 파일의 환경 변수 사용
// $cfg['Servers'][$i]['password'] = getenv('MARIADB_PASSWORD'); // .env 파일의 환경 변수 사용
$cfg['Servers'][$i]['AllowNoPassword'] = false; // 빈 비밀번호 허용 안함

/* End of servers configuration */

// =========================================================================
// !!! 이 값은 반드시 32자 이상의 임의의 문자열로 변경하세요 !!!
// 예를 들어, openssl rand -base64 32 명령으로 생성할 수 있습니다.
$cfg['blowfish_secret'] = '5ll34090@gmail.comsoyjefu@theprepared.kr';
// =========================================================================

$cfg['DefaultLang'] = 'ko'; // 기본 언어 설정
$cfg['ServerDefault'] = 1; // 기본 접속 서버 인덱스 (1은 MariaDB, 2는 PostgreSQL)
$cfg['UploadDir'] = ''; // 업로드 디렉토리 (필요시 설정)
$cfg['SaveDir'] = '';   // 저장 디렉토리 (필요시 설정)
?>