from typing import List, Optional
from fastapi import APIRouter, HTTPException, status

from database import get_db_connection
from models import TodoCreate, TodoUpdate, TodoResponse

router = APIRouter(prefix="/todos", tags=["todos"])

@router.post("/", response_model=TodoResponse, status_code=status.HTTP_201_CREATED)
def create_todo(todo: TodoCreate):
    """Create a new todo item (Задание 8.2)"""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO todos (title, description, completed) VALUES (?, ?, 0)",
            (todo.title, todo.description)
        )
        conn.commit()
        
        todo_id = cursor.lastrowid
        cursor.execute("SELECT id, title, description, completed FROM todos WHERE id = ?", (todo_id,))
        row = cursor.fetchone()
        
        return dict(row)

@router.get("/{todo_id}", response_model=TodoResponse)
def get_todo(todo_id: int):
    """Get a single todo by ID (Задание 8.2)"""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT id, title, description, completed FROM todos WHERE id = ?", (todo_id,))
        row = cursor.fetchone()
        
        if not row:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Todo with id {todo_id} not found"
            )
        
        return dict(row)

@router.get("/", response_model=List[TodoResponse])
def get_all_todos():
    """Get all todos"""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT id, title, description, completed FROM todos")
        rows = cursor.fetchall()
        return [dict(row) for row in rows]

@router.put("/{todo_id}", response_model=TodoResponse)
def update_todo(todo_id: int, todo_update: TodoUpdate):
    """Update a todo item (Задание 8.2)"""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        
        # Check if todo exists
        cursor.execute("SELECT id FROM todos WHERE id = ?", (todo_id,))
        if not cursor.fetchone():
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Todo with id {todo_id} not found"
            )
        
        # Build update query dynamically
        update_fields = []
        values = []
        
        if todo_update.title is not None:
            update_fields.append("title = ?")
            values.append(todo_update.title)
        
        if todo_update.description is not None:
            update_fields.append("description = ?")
            values.append(todo_update.description)
        
        if todo_update.completed is not None:
            update_fields.append("completed = ?")
            values.append(1 if todo_update.completed else 0)
        
        if update_fields:
            query = f"UPDATE todos SET {', '.join(update_fields)} WHERE id = ?"
            values.append(todo_id)
            cursor.execute(query, values)
            conn.commit()
        
        # Return updated todo
        cursor.execute("SELECT id, title, description, completed FROM todos WHERE id = ?", (todo_id,))
        row = cursor.fetchone()
        return dict(row)

@router.delete("/{todo_id}")
def delete_todo(todo_id: int):
    """Delete a todo item (Задание 8.2)"""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        
        cursor.execute("SELECT id FROM todos WHERE id = ?", (todo_id,))
        if not cursor.fetchone():
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Todo with id {todo_id} not found"
            )
        
        cursor.execute("DELETE FROM todos WHERE id = ?", (todo_id,))
        conn.commit()
        
        return {"message": f"Todo {todo_id} deleted successfully"}