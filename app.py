from flask import Flask, request, jsonify

app = Flask(__name__)

# Mock database for MVP purposes (stores order status)
orders_db = {
    "101": {"restaurant_id": "R1", "status": "Pending", "items": ["Burger", "Fries"]},
    "102": {"restaurant_id": "R1", "status": "Pending", "items": ["Pizza"]},
}

@app.route('/restaurant/<restaurant_id>/order/<order_id>', methods=['PATCH'])
def update_order_status(restaurant_id, order_id):
    data = request.json
    new_status = data.get('status')

    # 1. Validate the input (Accept or Reject only)
    if new_status not in ["Accepted", "Rejected"]:
        return jsonify({"error": "Invalid status. Use 'Accepted' or 'Rejected'."}), 400

    # 2. Check if the order exists in our "database"
    order = orders_db.get(order_id)
    if not order:
        return jsonify({"error": "Order not found."}), 404

    # 3. Security Check: Does this order belong to the restaurant making the request?
    if order["restaurant_id"] != restaurant_id:
        return jsonify({"error": "Unauthorized. Restaurant ID mismatch."}), 403

    # 4. Update the status and return the result
    order["status"] = new_status
    return jsonify({
        "message": f"Order {order_id} has been {new_status.lower()}.",
        "updated_order": order
    }), 200

if __name__ == '__main__':
    app.run(debug=True)