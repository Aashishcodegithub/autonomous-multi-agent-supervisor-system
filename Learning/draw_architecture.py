import matplotlib.pyplot as plt
import matplotlib.patches as patches

def draw_diagram():
    # Set up dark-mode style figure
    fig, ax = plt.subplots(figsize=(11, 7.5), facecolor='#121214')
    ax.set_facecolor('#121214')
    
    # Hide axes
    ax.axis('off')
    ax.set_xlim(-1, 10)
    ax.set_ylim(-0.5, 9.5)
    
    # Color palette
    c_user = '#9b5de5'       # Purple
    c_state = '#00f5d4'      # Teal
    c_super = '#f15bb5'      # Pink
    c_worker = '#00bbf9'     # Blue
    c_memory = '#fee440'     # Yellow
    c_tool = '#f77f00'       # Orange
    c_text_dark = '#0f0f10'
    c_text_light = '#f8f9fa'
    
    # Draw title
    ax.text(4.5, 9.1, "LangGraph Supervisor Multi-Agent Architecture", 
            color=c_text_light, fontsize=16, fontweight='bold', ha='center')
    
    # Helper to draw a node (rounded/regular box)
    def draw_box(x, y, w, h, text, bg_color, text_color=c_text_dark, rx=0.15):
        rect = patches.FancyBboxPatch((x, y), w, h, boxstyle=f"round,pad={rx}",
                                      facecolor=bg_color, edgecolor=bg_color, linewidth=0)
        ax.add_patch(rect)
        # Handle newlines in text to center vertically
        lines = text.split('\n')
        y_offset = y + h/2.0 - (len(lines)-1)*0.15
        for i, line in enumerate(lines):
            ax.text(x + w/2.0, y_offset - i*0.3, line, color=text_color, 
                    fontsize=10.5, fontweight='semibold', ha='center', va='center')

    # Helper to draw a node with custom font size
    def draw_box_small(x, y, w, h, text, bg_color, text_color=c_text_dark, rx=0.1):
        rect = patches.FancyBboxPatch((x, y), w, h, boxstyle=f"round,pad={rx}",
                                      facecolor=bg_color, edgecolor=bg_color, linewidth=0)
        ax.add_patch(rect)
        lines = text.split('\n')
        y_offset = y + h/2.0 - (len(lines)-1)*0.12
        for i, line in enumerate(lines):
            ax.text(x + w/2.0, y_offset - i*0.24, line, color=text_color, 
                    fontsize=9, fontweight='semibold', ha='center', va='center')

    # Helper to draw arrow
    def draw_arrow(x1, y1, x2, y2, color='#f8f9fa', lw=1.8):
        ax.annotate('', xy=(x2, y2), xytext=(x1, y1),
                    arrowprops=dict(arrowstyle="-|>", color=color, lw=lw,
                                    patchA=None, patchB=None, shrinkA=8, shrinkB=8))
        
    # Helper to draw bidirectional arrow
    def draw_bi_arrow(x1, y1, x2, y2, color='#f8f9fa', lw=1.8):
        ax.annotate('', xy=(x2, y2), xytext=(x1, y1),
                    arrowprops=dict(arrowstyle="<|-|>", color=color, lw=lw,
                                    patchA=None, patchB=None, shrinkA=8, shrinkB=8))

    # --- Draw Nodes ---
    # 1. User
    draw_box(3.5, 7.5, 2.0, 0.8, "USER\n(Submits Query)", c_user, c_text_light)
    
    # 2. Shared State
    draw_box(3.2, 5.8, 2.6, 0.9, "SHARED STATE\nMessages List", c_state, c_text_dark)
    
    # 3. Persistent Memory / Checkpointer
    draw_box(7.0, 5.8, 2.4, 0.9, "MemorySaver\nCheckpointer\n(thread_id)", c_memory, c_text_dark)
    
    # 4. Supervisor Node
    draw_box(3.0, 4.0, 3.0, 1.0, "SUPERVISOR NODE\nDecides Next Actor\n(Gemini Structured Output)", c_super, c_text_light)
    
    # 5. Math Worker
    draw_box(0.5, 2.0, 2.4, 0.9, "MATH WORKER\nCalculates equations\n(Gemini 2.5/3.5)", c_worker, c_text_dark)
    
    # 6. Math Tools
    draw_box_small(0.2, 0.4, 3.0, 0.7, "ARITHMETIC TOOLS\n(Add, Subtract, Multiply, Divide)", c_tool, c_text_light)
    
    # 7. Writer Worker
    draw_box(5.8, 2.0, 2.6, 0.9, "WRITER WORKER\nFormats response &\nadds fun facts", c_worker, c_text_dark)
    
    # 8. End Node
    draw_box(3.5, 0.4, 2.0, 0.7, "END / FINISH\n(Final Response)", c_state, c_text_dark)

    # --- Draw Arrows ---
    # User to State
    draw_arrow(4.5, 7.5, 4.5, 6.7, c_user)
    
    # State <--> Checkpointer
    draw_bi_arrow(5.8, 6.25, 7.0, 6.25, c_memory)
    
    # State to Supervisor
    draw_arrow(4.5, 5.8, 4.5, 5.0, c_state)
    
    # Supervisor -> Workers (Conditional Edges)
    draw_arrow(3.5, 4.0, 2.0, 2.9, c_super)
    draw_arrow(5.5, 4.0, 7.0, 2.9, c_super)
    draw_arrow(4.5, 4.0, 4.5, 1.1, c_super) # Direct to Finish
    
    # Math Worker <--> Tools
    draw_bi_arrow(1.7, 2.0, 1.7, 1.1, c_tool)
    
    # Math Worker -> Writer Worker (Cascaded routing)
    draw_arrow(2.9, 2.45, 5.8, 2.45, c_worker)
    
    # Writer Worker -> End
    draw_arrow(7.1, 2.0, 5.2, 1.1, c_worker)

    # Label Conditional Routes
    ax.text(2.2, 3.6, "math_worker", color=c_text_light, fontsize=8.5, rotation=33, ha='center')
    ax.text(6.8, 3.6, "writer_worker", color=c_text_light, fontsize=8.5, rotation=-33, ha='center')
    ax.text(4.85, 3.2, "FINISH", color=c_text_light, fontsize=8.5, ha='center')
    ax.text(4.35, 2.6, "cascade", color=c_text_light, fontsize=8.5, ha='center')

    # Adjust layout and save
    plt.tight_layout()
    plt.savefig('architecture.png', dpi=200, facecolor='#121214', bbox_inches='tight')
    plt.close()
    print("✅ Architecture diagram drawn successfully and saved to architecture.png")

if __name__ == '__main__':
    draw_diagram()
