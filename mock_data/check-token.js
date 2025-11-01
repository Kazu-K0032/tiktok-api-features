/**
 * 現在のユーザー情報を取得して、アクセストークン / Open IDを出力する
 * webコンソールで実行する
 */
fetch('/api/users')
  .then(res => res.json())
  .then(data => {
    if (data.users && data.users.length > 0) {
      const currentUser = data.users.find(u => u.open_id === data.current_user_open_id) || data.users[0];
      console.log('アクセストークン:', currentUser.access_token);
      console.log('Open ID:', currentUser.open_id);
    }
  });
