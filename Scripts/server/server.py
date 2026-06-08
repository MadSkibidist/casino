import socket
import ssl
import threading
import random
import smtplib
import time
from email.mime.text import MIMEText

from shared.protocol import (encode, decode,
                              MSG_LOGIN, MSG_SIGNUP, MSG_AUTH_OK, MSG_AUTH_FAIL)
from server.database        import CasinoDatabase
from server.room_manager    import RoomManager
from server.chat_manager    import ChatManager
from server.blackjack_logic import BlackjackTable
from server.roulette_logic  import RouletteTable
from server.poker_logic     import PokerTable

PORT         = 5555
SMTP_SERVER  = "smtp.gmail.com"
SMTP_PORT    = 587
SENDER_EMAIL = "casinoproject65@gmail.com"
SENDER_PASS  = "ahbn hclh pnsk oykn"

db   = CasinoDatabase()
room = RoomManager()
chat = ChatManager()

bj_table       = BlackjackTable(db=db)
roulette_table = RouletteTable(db=db)
poker_table    = PokerTable(db=db)

lobby_tables: dict = {
    "BLACKJACK": bj_table,
    "ROULETTE":  roulette_table,
    "POKER":     poker_table,
}

active_connections: dict = {}
active_connections_lock  = threading.Lock()
active_games: dict = {}
games_lock = threading.Lock()


def _send_otp_email(to_email: str, username: str, code: str) -> bool:
    # Always print to console as backup
    print(f"[OTP] {username} ({to_email}): {code}")

    if not SENDER_PASS:
        return True

    try:
        import ssl
        from email.message import EmailMessage

        em = EmailMessage()
        em["From"] = SENDER_EMAIL
        em["To"] = to_email
        em["Subject"] = "Casino Project - Verification Code"
        em.set_content(
            f"Hello {username},\n\n"
            f"Your verification code is: {code}\n\n"
            f"Valid for 5 minutes.\n\nCasino Project"
        )

        context = ssl.create_default_context()

        with smtplib.SMTP_SSL("smtp.gmail.com", 465, context=context) as smtp:
            smtp.login(SENDER_EMAIL, SENDER_PASS)
            smtp.sendmail(SENDER_EMAIL, to_email, em.as_string())

        print(f"[EMAIL] Sent to {to_email}")
        return True

    except Exception as e:
        print(f"[SMTP ERROR] {e}")
        return False


def _handle_signup(username: str, password: str, email: str):
    t = time.time()
    pending = db.CheckPendingUser(username, email)
    if pending:
        db_user, otp_expiry, is_verified = pending
        if is_verified:
            return False, "Username or email already exists!"
        if t < otp_expiry:
            return False, "Account is pending email verification."
        db.DeleteUser(db_user)
    code = str(random.randint(1000, 9999))
    db.SaveUser(username, password, email, code, t + 300)
    return True, code


def _handle_login(username: str, password: str):
    if not db.IsPasswordOK(username, password):
        return False, "Invalid username or password.", None
    with active_connections_lock:
        if username in active_connections:
            return False, "Already logged in from another session.", None
    code  = str(random.randint(1000, 9999))
    email = db.GetUserEmail(username)
    db.UpdateOTP(username, code, time.time() + 300)
    return True, code, email


def _handle_forgot(username: str, email: str):
    if not db.IsUserExist(username):
        return False, "User not found."
    if db.GetUserEmail(username) != email:
        return False, "Username and email do not match."
    code = str(random.randint(1000, 9999))
    db.UpdateOTP(username, code, time.time() + 300)
    return True, code


def _verify_otp(username: str, code: str, purpose: str):
    row = db.GetOTPInfo(username)
    if not row:
        return False, "Session not found."
    db_code, expiry = row
    if time.time() > expiry:
        return False, "Code has expired!"
    if code != db_code:
        return False, "Wrong code — try again."
    if purpose in ("REG", "LOG"):
        db.SetUserVerified(username)
    return True, "OK"


def _check_ttt_winner(board: list) -> str | None:
    wins = ([0,1,2],[3,4,5],[6,7,8],[0,3,6],[1,4,7],[2,5,8],[0,4,8],[2,4,6])
    for w in wins:
        if board[w[0]] and board[w[0]] == board[w[1]] == board[w[2]]:
            return board[w[0]]
    if "" not in board:
        return "TIE"
    return None


def _broadcast_lobby(msg: dict):
    raw = encode(msg)
    for sock in room.get_all_sockets():
        try:
            sock.sendall(raw)
        except Exception:
            pass


def _recv_line(sock) -> bytes | None:
    buf = b""
    while True:
        try:
            chunk = sock.recv(4096)
        except Exception:
            return None
        if not chunk:
            return None
        buf += chunk
        if b"\n" in buf:
            line, _ = buf.split(b"\n", 1)
            return line


def handle_client(sock):
    my_username        = None
    is_authenticated   = False
    current_table_type = None

    try:
        while not is_authenticated:
            raw = _recv_line(sock)
            if raw is None:
                return
            req = decode(raw)
            cmd = req.get("cmd", "")

            if cmd == MSG_SIGNUP:
                u, p, e = req.get("username","").strip(), req.get("password",""), req.get("email","").strip()
                ok, result = _handle_signup(u, p, e)
                if ok:
                    my_username = u
                    if _send_otp_email(e, u, result):
                        sock.sendall(encode({"cmd":"NEED_OTP","purpose":"REG","msg":"Verification code sent!"}))
                    else:
                        sock.sendall(encode({"cmd":MSG_AUTH_FAIL,"msg":"Could not send email."}))
                else:
                    sock.sendall(encode({"cmd":MSG_AUTH_FAIL,"msg":result}))

            elif cmd == MSG_LOGIN:
                u, p = req.get("username","").strip(), req.get("password","")
                ok, result, email = _handle_login(u, p)
                if ok:
                    my_username = u
                    if _send_otp_email(email, u, result):
                        sock.sendall(encode({"cmd":"NEED_OTP","purpose":"LOG","msg":"Verification code sent!"}))
                    else:
                        sock.sendall(encode({"cmd":MSG_AUTH_FAIL,"msg":"Could not send email."}))
                else:
                    sock.sendall(encode({"cmd":MSG_AUTH_FAIL,"msg":result}))

            elif cmd == "FORGOT_PASSWORD":
                u, e = req.get("username","").strip(), req.get("email","").strip()
                ok, result = _handle_forgot(u, e)
                if ok:
                    my_username = u
                    email = db.GetUserEmail(u)
                    if _send_otp_email(email, u, result):
                        sock.sendall(encode({"cmd":"NEED_OTP","purpose":"FORGOT","msg":"Reset code sent!"}))
                    else:
                        sock.sendall(encode({"cmd":MSG_AUTH_FAIL,"msg":"Email error."}))
                else:
                    sock.sendall(encode({"cmd":MSG_AUTH_FAIL,"msg":result}))

            elif cmd == "VERIFY_OTP":
                code, purpose = req.get("code","").strip(), req.get("purpose","LOG")
                if my_username:
                    ok, msg_text = _verify_otp(my_username, code, purpose)
                    if ok:
                        if purpose == "FORGOT":
                            sock.sendall(encode({"cmd":"GOTO_RESET","msg":"Enter new password."}))
                        else:
                            is_authenticated = True
                            with active_connections_lock:
                                active_connections[my_username] = sock
                            balance = db.GetBalance(my_username)
                            if balance < 1500:
                                db.UpdateBalance(my_username, 5000 - balance)
                                balance = 5000
                            sock.sendall(encode({"cmd": MSG_AUTH_OK, "msg": "Welcome!", "balance": balance}))
                    else:
                        sock.sendall(encode({"cmd":MSG_AUTH_FAIL,"msg":msg_text}))

            elif cmd == "RESET_PASSWORD":
                new_p = req.get("password","")
                if my_username and new_p:
                    db.UpdatePassword(my_username, new_p)
                    sock.sendall(encode({"cmd":MSG_AUTH_OK,"msg":"Password updated! Please log in."}))

        char_id = req.get("char_id", 0)
        balance = db.GetBalance(my_username)

        if not room.add_player(sock, my_username, char_id, balance):
            sock.sendall(encode({"cmd":"ROOM_FULL","msg":"Server room is full."}))
            return

        sock.sendall(encode({"cmd":"CHAT_HISTORY","history":chat.get_history()}))
        _broadcast_lobby({"cmd":"ROOM_STATE","players":room.get_room_state()})

        while True:
            raw = _recv_line(sock)
            if raw is None:
                break
            req = decode(raw)
            cmd = req.get("cmd","")

            if cmd == "JOIN_TABLE":
                table_type = req.get("table_type")
                if table_type in lobby_tables:
                    current_balance = db.GetBalance(my_username)
                    if current_balance < 1500:
                        db.UpdateBalance(my_username, 5000 - current_balance)
                        balance = 5000
                        room.update_balance(my_username, 5000)
                        sock.sendall(encode({
                            "cmd": "BACK_TO_LOBBY",
                            "balance": 5000,
                            "msg": "יתרתך אופסה ל-5000 אסימונים!"
                        }))

                    current_table_type = table_type
                    bet = int(req.get("bet", 100))
                    if table_type == "BLACKJACK":
                        lobby_tables[table_type].add_player(sock, my_username, bet)
                    else:
                        lobby_tables[table_type].add_player(sock, my_username)
                    sock.sendall(encode({"cmd": "JOIN_SUCCESS", "table": table_type}))

            elif cmd == "LEAVE_TABLE":
                if current_table_type in lobby_tables:
                    lobby_tables[current_table_type].remove_player(sock)
                current_table_type = None
                balance = db.GetBalance(my_username)
                room.update_balance(my_username, balance)
                sock.sendall(encode({"cmd":"BACK_TO_LOBBY","balance":balance}))
                _broadcast_lobby({"cmd":"ROOM_STATE","players":room.get_room_state()})

            elif cmd == "GAME_ACTION" and current_table_type == "BLACKJACK":
                bj_table.handle_action(my_username, req.get("action",""))

            elif cmd == "PLACE_BET" and current_table_type == "ROULETTE":
                ok, msg_text = roulette_table.place_bet(
                    my_username, int(req.get("amount",100)),
                    req.get("bet_type","COLOR"), req.get("bet_value"))
                sock.sendall(encode({"cmd":"BET_ACK","ok":ok,"msg":msg_text}))

            elif cmd == "POKER_ACTION" and current_table_type == "POKER":
                poker_table.handle_action(my_username, req.get("action","FOLD"), int(req.get("amount",0)))

            elif cmd == "MOVE":
                room.update_position(sock, req.get("x",400), req.get("y",400))
                _broadcast_lobby({"cmd":"ROOM_STATE","players":room.get_room_state()})

            elif cmd == "CHAT":
                text = req.get("text","").strip()
                if text:
                    chat.add_message(my_username, text)
                    _broadcast_lobby({"cmd":"CHAT","username":my_username,"text":text})

            elif cmd == "SEND_MSG":
                raw_text = req.get("text","").strip()
                if ":" not in raw_text:
                    sock.sendall(encode({"cmd":"CHAT_ERROR","msg":"Format: username:message"}))
                    continue
                target, body = raw_text.split(":",1)
                target, body = target.strip(), body.strip()
                if not db.IsUserExist(target):
                    sock.sendall(encode({"cmd":"CHAT_ERROR","msg":f"'{target}' does not exist."}))
                    continue
                with active_connections_lock:
                    tsock = active_connections.get(target)
                if body.lower() == "play":
                    if tsock:
                        tsock.sendall(encode({"cmd":"GAME_INVITE","from":my_username}))
                        sock.sendall(encode({"cmd":"CHAT_ACK","text":f"TicTacToe invite sent to {target}!"}))
                    else:
                        sock.sendall(encode({"cmd":"CHAT_ERROR","msg":f"'{target}' is offline."}))
                else:
                    if tsock:
                        tsock.sendall(encode({"cmd":"RECEIVE_MSG","sender":my_username,"text":body}))
                        sock.sendall(encode({"cmd":"CHAT_ACK","text":body}))
                    else:
                        sock.sendall(encode({"cmd":"CHAT_ERROR","msg":f"'{target}' is offline."}))

            elif cmd == "GAME_ACCEPT":
                host = req.get("host","")
                gid  = f"{host}_{my_username}"
                with games_lock:
                    active_games[gid] = {"p1":host,"p2":my_username,"board":[""]*9,"turn":host}
                with active_connections_lock:
                    p1_sock = active_connections.get(host)
                    p2_sock = active_connections.get(my_username)
                if p1_sock:
                    p1_sock.sendall(encode({"cmd":"START_GAME","game_id":gid,"role":"X","opponent":my_username,"turn":host}))
                if p2_sock:
                    p2_sock.sendall(encode({"cmd":"START_GAME","game_id":gid,"role":"O","opponent":host,"turn":host}))

            elif cmd == "GAME_MOVE":
                gid   = req.get("game_id","")
                index = int(req.get("index",-1))
                with games_lock:
                    game = active_games.get(gid)
                    if not game or game["turn"]!=my_username or index<0 or index>8 or game["board"][index]!="":
                        continue
                    role = "X" if my_username==game["p1"] else "O"
                    game["board"][index] = role
                    winner = _check_ttt_winner(game["board"])
                    game["turn"] = game["p2"] if my_username==game["p1"] else game["p1"]
                    payload = {"cmd":"GAME_UPDATE","board":game["board"],"turn":game["turn"],"winner":winner}
                    with active_connections_lock:
                        for player in (game["p1"], game["p2"]):
                            ps = active_connections.get(player)
                            if ps:
                                try:
                                    ps.sendall(encode(payload))
                                except Exception:
                                    pass
                    if winner:
                        del active_games[gid]

            elif cmd == "SET_CHAR":
                new_id = int(req.get("char_id",0))
                room.update_char(sock, new_id)
                _broadcast_lobby({"cmd":"ROOM_STATE","players":room.get_room_state()})

    except Exception as e:
        print(f"[SERVER] Error for {my_username}: {e}")

    finally:
        if current_table_type in lobby_tables:
            try:
                lobby_tables[current_table_type].remove_player(sock)
            except Exception:
                pass
        room.remove_player(sock)
        if my_username:
            with active_connections_lock:
                if active_connections.get(my_username) is sock:
                    del active_connections[my_username]
        _broadcast_lobby({"cmd":"ROOM_STATE","players":room.get_room_state()})
        try:
            sock.close()
        except Exception:
            pass
        print(f"[SERVER] {my_username or 'unknown'} disconnected.")


def main():
    raw_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    raw_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    raw_sock.bind(("0.0.0.0", PORT))
    raw_sock.listen(20)
    try:
        ctx = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
        ctx.load_cert_chain("cert.pem", "key.pem")
        server_sock = ctx.wrap_socket(raw_sock, server_side=True)
        print(f"[SERVER] SSL server listening on port {PORT}")
    except Exception as e:
        print(f"[SERVER] SSL unavailable ({e}) — plain TCP on port {PORT}")
        server_sock = raw_sock
    print("[SERVER] Ready.")
    while True:
        try:
            client_sock, addr = server_sock.accept()
            threading.Thread(target=handle_client, args=(client_sock,), daemon=True).start()
            print(f"[SERVER] New connection from {addr}")
        except KeyboardInterrupt:
            break
        except Exception as e:
            print(f"[SERVER] Accept error: {e}")


if __name__ == "__main__":
    main()