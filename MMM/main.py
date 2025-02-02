from flask import Flask, request, jsonify
import chess
import chess.engine
from flask_cors import CORS

app = Flask(__name__)
CORS(app)  # Enable CORS for frontend communication

# Initialize chess board
board = chess.Board()
stockfish_path = "C:\\Users\\dpava\\OneDrive\\Desktop\\VRS Project\\stockfish-windows-x86.exe"

# Move history for undo/redo functionality
move_history = []
redo_stack = []
ai_difficulty = 10  # Default AI difficulty
player_color = "white"  # Default player color

def get_board_state():
    return {
        "fen": board.fen(),
        "legal_moves": [move.uci() for move in board.legal_moves],
        "game_over": board.is_game_over(),
        "turn": "white" if board.turn == chess.WHITE else "black",
        "is_check": board.is_check(),
        "is_checkmate": board.is_checkmate(),
        "is_stalemate": board.is_stalemate()
    }

@app.route("/set_difficulty", methods=["POST"])
def set_difficulty():
    global ai_difficulty
    data = request.json
    difficulty = data.get("difficulty", "medium").lower()
    ai_difficulty = {"easy": 1, "medium": 10, "hard": 20}.get(difficulty, 10)
    return jsonify({"message": "AI difficulty set", "difficulty": difficulty})

@app.route("/set_color", methods=["POST"])
def set_color():
    global player_color
    data = request.json
    color = data.get("color", "white").lower()
    if color in ["white", "black"]:
        player_color = color
        return jsonify({"message": "Player color set", "color": color})
    return jsonify({"error": "Invalid color choice"}), 400

@app.route("/reset", methods=["POST"])
def reset_board():
    global board, move_history, redo_stack
    board = chess.Board()
    move_history.clear()
    redo_stack.clear()
    return jsonify(get_board_state())

@app.route("/move", methods=["POST"])
def make_move():
    data = request.json
    move_uci = data.get("move")
    if not move_uci:
        return jsonify({"error": "Move not provided"}), 400
    try:
        move = chess.Move.from_uci(move_uci)
        if move in board.legal_moves:
            board.push(move)
            move_history.append(move)
            redo_stack.clear()
            return jsonify(get_board_state())
        else:
            return jsonify({"error": "Illegal move"}), 400
    except Exception:
        return jsonify({"error": "Invalid move format"}), 400

@app.route("/ai_move", methods=["GET"])
def ai_move():
    with chess.engine.SimpleEngine.popen_uci(stockfish_path) as engine:
        engine.configure({"Skill Level": ai_difficulty})
        result = engine.play(board, chess.engine.Limit(time=1.0))
        board.push(result.move)
        move_history.append(result.move)
        redo_stack.clear()
    return jsonify(get_board_state())

@app.route("/undo", methods=["POST"])
def undo_move():
    if move_history:
        redo_stack.append(board.pop())
    return jsonify(get_board_state())

@app.route("/redo", methods=["POST"])
def redo_move():
    if redo_stack:
        move_history.append(redo_stack.pop())
        board.push(move_history[-1])
    return jsonify(get_board_state())

@app.route("/hint", methods=["GET"])
def suggest_best_move():
    with chess.engine.SimpleEngine.popen_uci(stockfish_path) as engine:
        info = engine.analyse(board, chess.engine.Limit(depth=15))
        best_move = info["pv"][0].uci()
        eval_score = info["score"].relative.score(mate_score=10000)
        eval_display = "Checkmate!" if abs(eval_score) > 9000 else f"{eval_score / 100:.2f}"
    return jsonify({"best_move": best_move, "evaluation": eval_display})

@app.route("/board", methods=["GET"])
def get_board():
    return jsonify(get_board_state())

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=5000, debug=True)
