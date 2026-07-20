import matplotlib.pyplot as plt
import matplotlib.patches as patches

def draw_diagram():
    # Set up dark-mode style figure
    fig, ax = plt.subplots(figsize=(14, 9), facecolor='#121214')
    ax.set_facecolor('#121214')
    
    # Hide axes
    ax.axis('off')
    ax.set_xlim(-1, 13)
    ax.set_ylim(-1, 10.5)
    
    # Color palette
    c_user = '#9b5de5'       # Purple
    c_backend = '#00f5d4'    # Teal
    c_super = '#f15bb5'      # Pink
    c_worker = '#00bbf9'     # Blue
    c_db = '#fee440'         # Yellow
    c_tool = '#f77f00'       # Orange
    c_erp = '#38b000'        # Green
    c_text_dark = '#0f0f10'
    c_text_light = '#f8f9fa'
    
    # Draw title
    ax.text(6.0, 10.0, "ERP AI Agentic Supervisor Pipeline", 
            color=c_text_light, fontsize=18, fontweight='bold', ha='center')
    
    # Helper to draw a node (rounded/regular box)
    def draw_box(x, y, w, h, text, bg_color, text_color=c_text_dark, rx=0.15, fontsize=10.5):
        rect = patches.FancyBboxPatch((x, y), w, h, boxstyle=f"round,pad={rx}",
                                      facecolor=bg_color, edgecolor=bg_color, linewidth=0)
        ax.add_patch(rect)
        lines = text.split('\n')
        y_offset = y + h/2.0 - (len(lines)-1)*0.15
        for i, line in enumerate(lines):
            ax.text(x + w/2.0, y_offset - i*0.3, line, color=text_color, 
                    fontsize=fontsize, fontweight='semibold', ha='center', va='center')

    # Helper to draw arrow
    def draw_arrow(x1, y1, x2, y2, color='#f8f9fa', lw=1.8):
        ax.annotate('', xy=(x2, y2), xytext=(x1, y1),
                    arrowprops=dict(arrowstyle="-|>", color=color, lw=lw,
                                    patchA=None, patchB=None, shrinkA=8, shrinkB=8))
        
    def draw_bi_arrow(x1, y1, x2, y2, color='#f8f9fa', lw=1.8):
        ax.annotate('', xy=(x2, y2), xytext=(x1, y1),
                    arrowprops=dict(arrowstyle="<|-|>", color=color, lw=lw,
                                    patchA=None, patchB=None, shrinkA=8, shrinkB=8))

    # --- Draw Nodes ---
    
    # User / UI
    draw_box(4.5, 8.5, 3.0, 0.8, "Streamlit Dashboard\n(User UI)", c_user, c_text_light)
    
    # Backend
    draw_box(4.5, 6.8, 3.0, 0.9, "FastAPI Backend\n(/api/run)", c_backend, c_text_dark)
    
    # Vector DB
    draw_box(0.5, 5.0, 2.5, 0.9, "FAISS Vector DB\n(Semantic Resolution)", c_db, c_text_dark)
    
    # Supervisor Node
    draw_box(4.5, 5.0, 3.0, 1.0, "SUPERVISOR AGENT\n(Intent Routing & Multi-Chain)", c_super, c_text_light)
    
    # Specialist Agents
    w_agent = 2.0
    h_agent = 0.8
    y_agents = 3.0
    
    draw_box(0.5, y_agents, w_agent, h_agent, "Dashboard\nAgent", c_worker, c_text_dark, fontsize=9.5)
    draw_box(3.0, y_agents, w_agent, h_agent, "Report\nAgent", c_worker, c_text_dark, fontsize=9.5)
    draw_box(5.5, y_agents, w_agent, h_agent, "Graph\nAgent", c_worker, c_text_dark, fontsize=9.5)
    draw_box(8.0, y_agents, w_agent, h_agent, "Table\nAgent", c_worker, c_text_dark, fontsize=9.5)
    draw_box(10.5, y_agents, w_agent, h_agent, "Summary\nAgent", c_worker, c_text_dark, fontsize=9.5)
    
    # Tools Layer
    draw_box(2.5, 1.2, 8.0, 0.8, "Tool Layer\n(AST Sandbox, Python Executor, Data Normalizer)", c_tool, c_text_light)
    
    # ERP Target
    draw_box(4.5, -0.6, 4.0, 0.8, "ERP Target / XML API", c_erp, c_text_light)

    # --- Draw Arrows ---
    
    # UI -> API
    draw_bi_arrow(6.0, 8.5, 6.0, 7.7, c_user)
    
    # API -> Supervisor
    draw_bi_arrow(6.0, 6.8, 6.0, 6.0, c_backend)
    
    # FAISS <-> Supervisor
    draw_bi_arrow(3.0, 5.5, 4.5, 5.5, c_db)
    
    # Supervisor -> Agents
    sup_x = 6.0
    sup_y = 5.0
    
    # Dashboard
    draw_arrow(sup_x, sup_y, 1.5, y_agents+0.8, c_super)
    # Report
    draw_arrow(sup_x, sup_y, 4.0, y_agents+0.8, c_super)
    # Graph
    draw_arrow(sup_x, sup_y, 6.5, y_agents+0.8, c_super)
    # Table
    draw_arrow(sup_x, sup_y, 9.0, y_agents+0.8, c_super)
    # Summary
    draw_arrow(sup_x, sup_y, 11.5, y_agents+0.8, c_super)
    
    # Agents -> Tools (just representative arrows from middle area)
    draw_arrow(6.5, y_agents, 6.5, 2.0, c_worker)
    draw_arrow(4.0, y_agents, 4.0, 2.0, c_worker)
    draw_arrow(9.0, y_agents, 9.0, 2.0, c_worker)
    
    # Tools -> ERP
    draw_bi_arrow(6.5, 1.2, 6.5, 0.2, c_erp)
    
    # Adjust layout and save
    plt.tight_layout()
    plt.savefig('architecture.png', dpi=200, facecolor='#121214', bbox_inches='tight')
    plt.close()
    print("✅ Architecture diagram drawn successfully and saved to architecture.png")

if __name__ == '__main__':
    draw_diagram()
