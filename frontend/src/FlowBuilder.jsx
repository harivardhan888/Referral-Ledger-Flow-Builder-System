import React, { useState, useRef, useCallback } from 'react';
import ReactFlow, {
  ReactFlowProvider,
  addEdge,
  useNodesState,
  useEdgesState,
  Controls,
  Background,
  Handle,
  Position
} from 'reactflow';
import 'reactflow/dist/style.css';
import axios from 'axios';

// -- Custom Nodes --

const ConditionNode = ({ id, data }) => {
  return (
    <div className="glass-panel" style={{ padding: '15px', minWidth: '200px', borderLeft: '4px solid #f59e0b' }}>
      <Handle type="target" position={Position.Top} />
      <div style={{ fontSize: '10px', textTransform: 'uppercase', color: '#f59e0b', fontWeight: 'bold' }}>Condition</div>
      <div style={{ marginTop: '5px' }}>
          <select 
            className="nodrag"
            value={data.field || ''} 
            onChange={(evt) => data.onChange(id, 'field', evt.target.value)}
            style={{ width: '100%', marginBottom: '5px' }}
          >
              <option value="" disabled>Select Field</option>
              <option value="referrer.status">Referrer Status</option>
              <option value="referred.action">Referred Action</option>
          </select>
          <div style={{ display: 'flex', gap: '5px' }}>
            <select 
                className="nodrag"
                value={data.operator || 'eq'} 
                onChange={(evt) => data.onChange(id, 'operator', evt.target.value)}
                style={{ width: '60px' }}
            >
                <option value="eq">=</option>
                <option value="contains">Has</option>
            </select>
            <input 
                value={data.value || ''} 
                className="nodrag"
                onChange={(evt) => data.onChange(id, 'value', evt.target.value)}
                placeholder="Value..."
                style={{ flex: 1 }}
            />
          </div>
      </div>
      <Handle type="source" position={Position.Bottom} />
    </div>
  );
};

const ActionNode = ({ id, data }) => {
  return (
    <div className="glass-panel" style={{ padding: '15px', minWidth: '200px', borderLeft: '4px solid #10b981' }}>
      <Handle type="target" position={Position.Top} />
      <div style={{ fontSize: '10px', textTransform: 'uppercase', color: '#10b981', fontWeight: 'bold' }}>Action</div>
      <div style={{ marginTop: '5px' }}>
         <select 
            className="nodrag"
            value={data.actionType || 'credit_reward'} 
            onChange={(evt) => data.onChange(id, 'actionType', evt.target.value)}
            style={{ width: '100%', marginBottom: '5px' }}
          >
              <option value="credit_reward">Credit Reward</option>
              {/* <option value="send_email">Send Email</option> */}
          </select>
          <input 
            type="number" 
            className="nodrag"
            value={data.params?.amount || 0} 
            onChange={(evt) => data.onChange(id, 'params', { ...data.params, amount: parseFloat(evt.target.value) })}
            placeholder="Amount"
            style={{ width: '100%' }}
          />
      </div>
    </div>
  );
};

const nodeTypes = {
  condition: ConditionNode,
  action: ActionNode,
};

const initialNodes = [
  { id: '1', type: 'input', data: { label: 'Start Flow' }, position: { x: 250, y: 5 }, className: 'glass-panel' },
];

let id = 0;
const getId = () => `dndnode_${id++}`;

const FlowBuilder = () => {
  const reactFlowWrapper = useRef(null);
  const [nodes, setNodes, onNodesChange] = useNodesState(initialNodes);
  const [edges, setEdges, onEdgesChange] = useEdgesState([]);
  const [reactFlowInstance, setReactFlowInstance] = useState(null);
  const [testResult, setTestResult] = useState(null);

  const onConnect = useCallback((params) => setEdges((eds) => addEdge(params, eds)), []);

  const onDragOver = useCallback((event) => {
    event.preventDefault();
    event.dataTransfer.dropEffect = 'move';
  }, []);

  const onNodeDataChange = (id, field, value) => {
      setNodes((nds) =>
        nds.map((node) => {
          if (node.id !== id) return node;
          const newData = { ...node.data, [field]: value };
          return { ...node, data: newData };
        })
      );
  };

  const onDrop = useCallback(
    (event) => {
      event.preventDefault();

      const type = event.dataTransfer.getData('application/reactflow');
      if (typeof type === 'undefined' || !type) return;

      const position = reactFlowInstance.project({
        x: event.clientX - reactFlowWrapper.current.getBoundingClientRect().left,
        y: event.clientY - reactFlowWrapper.current.getBoundingClientRect().top,
      });
      const newNode = {
        id: getId(),
        type,
        position,
        data: { label: `${type} node`, onChange: onNodeDataChange },
      };

      setNodes((nds) => nds.concat(newNode));
    },
    [reactFlowInstance]
  );

  const saveFlow = async () => {
      // 1. Convert Graph to Rule JSON
      // Simple traversal: find all conditions and actions
      const conditions = nodes
        .filter(n => n.type === 'condition')
        .map(n => ({
            field: n.data.field,
            operator: n.data.operator || 'eq',
            value: n.data.value
        }));
      
      const actions = nodes
        .filter(n => n.type === 'action')
        .map(n => ({
            action_type: n.data.actionType || 'credit_reward',
            params: n.data.params || {}
        }));

      const rule = {
          id: 'generated_rule',
          name: 'Visual Flow Rule',
          conditions,
          actions,
          operator: 'AND' 
      };

      console.log("Generated Rule:", rule);
      
      try {
        // Save (Mock)
        await axios.post('http://127.0.0.1:8000/flows', { id: 'latest_flow', nodes, edges, generated_rule: rule });
        alert('Flow saved!');
      } catch (error) {
        console.error(error);
        alert('Error saving flow');
      }
  };

  const testFlow = async () => {
    // Mock Context
    const context = {
        referrer: { status: 'paid' },
        referred: { action: 'subscribes' }
    };
    
    // Get the generated rule matching current state
    const conditions = nodes
        .filter(n => n.type === 'condition')
        .map(n => ({
            field: n.data.field,
            operator: n.data.operator || 'eq',
            value: n.data.value
        }));
      
    const actions = nodes
    .filter(n => n.type === 'action')
    .map(n => ({
        action_type: n.data.actionType || 'credit_reward',
        params: n.data.params || {}
    }));

    const rule = { id: 'temp', name: 'Test', conditions, actions, operator: 'AND' };

    try {
        const res = await axios.post('http://127.0.0.1:8000/rules/evaluate', {
            context,
            rules: [rule]
        });
        setTestResult(res.data);
    } catch (e) {
        alert("Error testing rule");
    }
  };

  const generateWithAI = async () => {
      const prompt = window.prompt("Describe your rule (e.g., 'If referrer is paid and referred subscribes, give 500 credit')");
      if (!prompt) return;

      try {
          const res = await axios.post('http://127.0.0.1:8000/rules/generate', { prompt });
          const rule = res.data;
          
          // Reconstruct nodes from rule
          const newNodes = [
              { id: '1', type: 'input', data: { label: 'Start Flow' }, position: { x: 250, y: 5 }, className: 'glass-panel' }
          ];
          
          let yOffset = 150;
          rule.conditions.forEach((cond, idx) => {
              newNodes.push({
                  id: getId(),
                  type: 'condition',
                  position: { x: 250, y: yOffset },
                  data: { 
                      label: 'Condition', 
                      field: cond.field, 
                      operator: cond.operator, 
                      value: cond.value,
                      onChange: onNodeDataChange 
                  }
              });
              yOffset += 150;
          });

          rule.actions.forEach((act, idx) => {
             newNodes.push({
                 id: getId(),
                 type: 'action',
                 position: { x: 250, y: yOffset },
                 data: {
                     label: 'Action',
                     actionType: act.action_type,
                     params: act.params,
                     onChange: onNodeDataChange
                 }
             });
             yOffset += 150;
          });

          // Create simple edges
          const newEdges = [];
          for(let i=0; i<newNodes.length-1; i++) {
              newEdges.push({
                  id: `e${i}-${i+1}`,
                  source: newNodes[i].id,
                  target: newNodes[i+1].id,
                  type: 'smoothstep'
              });
          }

          setNodes(newNodes);
          setEdges(newEdges);
      } catch (e) {
          console.error(e);
          alert("Error generating rule from AI: " + e.message);
      }
  };

  return (
    <div className="dndflow" style={{ width: '100%', height: '100vh', display: 'flex' }}>
      <div className="glass-panel" style={{ width: '250px', padding: '20px', margin: '20px', zIndex: 10 }}>
        <h3 className="gradient-text">Flow Components</h3>
        <div style={{ marginBottom: '20px', color: '#94a3b8', fontSize: '14px' }}>Drag these to the canvas</div>
        
        <div className="dndnode input glass-panel" onDragStart={(event) => event.dataTransfer.setData('application/reactflow', 'condition')} draggable style={{ padding: '10px', marginBottom: '10px', cursor: 'grab', borderLeft: '4px solid #f59e0b' }}>
          Condition Filter
        </div>
        <div className="dndnode output glass-panel" onDragStart={(event) => event.dataTransfer.setData('application/reactflow', 'action')} draggable style={{ padding: '10px', marginBottom: '10px', cursor: 'grab', borderLeft: '4px solid #10b981' }}>
          Action Node
        </div>

        <div style={{ marginTop: 'auto', paddingTop: '20px', borderTop: '1px solid rgba(255,255,255,0.1)' }}>
            <button onClick={saveFlow} style={{ width: '100%', marginBottom: '10px', backgroundColor: '#10b981' }}>Save Flow</button>
            <button onClick={testFlow} style={{ width: '100%', backgroundColor: '#4f46e5', marginBottom: '10px' }}>Test w/ Mock Data</button>
            <button onClick={generateWithAI} style={{ width: '100%', background: 'linear-gradient(to right, #ec4899, #8b5cf6)' }}>✨ Generate with AI</button>
        </div>
        
        {testResult && (
            <div style={{ marginTop: '20px', padding: '10px', background: 'rgba(0,0,0,0.3)', borderRadius: '8px', fontSize: '12px' }}>
                <strong>Test Result:</strong>
                <pre>{JSON.stringify(testResult, null, 2)}</pre>
            </div>
        )}
      </div>

      <div className="reactflow-wrapper" ref={reactFlowWrapper} style={{ flex: 1, height: '100%' }}>
        <ReactFlow
          nodes={nodes}
          edges={edges}
          onNodesChange={onNodesChange}
          onEdgesChange={onEdgesChange}
          onConnect={onConnect}
          onInit={setReactFlowInstance}
          onDrop={onDrop}
          onDragOver={onDragOver}
          nodeTypes={nodeTypes}
          fitView
        >
          <Controls />
          <Background color="#aaa" gap={16} />
        </ReactFlow>
      </div>
    </div>
  );
};

export default () => (
  <ReactFlowProvider>
    <FlowBuilder />
  </ReactFlowProvider>
);
