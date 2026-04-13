module bmssp_module
  implicit none
  integer, parameter :: MAX_NODES = 1000
  integer, parameter :: MAX_EDGES = 1000
  integer, parameter :: MAX_NAME_LEN = 64

  type :: Edge
    integer :: to
    real :: w
  end type Edge

  type :: Graph
    integer :: n
    integer :: deg(MAX_NODES)
    type(Edge) :: edges(MAX_NODES, MAX_EDGES)
  end type Graph

  type :: NodeDist
    integer :: node
    real :: dist
  end type NodeDist

  type :: DQueue
    integer :: M
    real :: B
    integer :: size
    type(NodeDist) :: data(MAX_NODES)
    integer :: pre_size
    type(NodeDist) :: prepend(MAX_NODES)
  end type DQueue

contains

  subroutine init_graph(g, n)
    type(Graph), intent(out) :: g
    integer, intent(in) :: n
    g%n = n
    g%deg = 0
  end subroutine init_graph

  subroutine add_edge(g, u, v, wt)
    type(Graph), intent(inout) :: g
    integer, intent(in) :: u, v
    real, intent(in) :: wt
    g%deg(u) = g%deg(u) + 1
    g%edges(u, g%deg(u)) = Edge(v, wt)
    if (g%deg(v) == 0) g%deg(v) = g%deg(v)
  end subroutine add_edge

  subroutine dq_init(q, M, B)
    type(DQueue), intent(out) :: q
    integer, intent(in) :: M
    real, intent(in) :: B
    q%M = M
    q%B = B
    q%size = 0
    q%pre_size = 0
  end subroutine dq_init

  subroutine dq_insert(q, node, dist)
    type(DQueue), intent(inout) :: q
    integer, intent(in) :: node
    real, intent(in) :: dist
    if (dist >= q%B) return
    q%size = q%size + 1
    q%data(q%size) = NodeDist(node, dist)
  end subroutine dq_insert

  subroutine dq_batch_prepend(q, items, count)
    type(DQueue), intent(inout) :: q
    type(NodeDist), intent(in) :: items(:)
    integer, intent(in) :: count
    integer :: i
    do i = 1, count
      if (items(i)%dist < q%B) then
        q%pre_size = q%pre_size + 1
        q%prepend(q%pre_size) = items(i)
      end if
    end do
  end subroutine dq_batch_prepend

  logical function dq_non_empty(q)
    type(DQueue), intent(in) :: q
    dq_non_empty = (q%pre_size > 0) .or. (q%size > 0)
  end function dq_non_empty

  subroutine dq_pull(q, Bi, nodes, count)
    type(DQueue), intent(inout) :: q
    real, intent(out) :: Bi
    integer, intent(out) :: nodes(:)
    integer, intent(out) :: count
    integer :: i, min_idx
    real :: min_dist

    if (q%pre_size > 0) then
      count = min(q%M, q%pre_size)
      Bi = q%prepend(1)%dist
      do i = 1, count
        nodes(i) = q%prepend(i)%node
      end do
      do i = 1, q%pre_size - count
        q%prepend(i) = q%prepend(i + count)
      end do
      q%pre_size = q%pre_size - count
      return
    end if

    if (q%size == 0) then
      Bi = q%B
      count = 0
      return
    end if

    min_dist = q%data(1)%dist
    min_idx = 1
    do i = 2, q%size
      if (q%data(i)%dist < min_dist) then
        min_dist = q%data(i)%dist
        min_idx = i
      end if
    end do
    Bi = min_dist
    nodes(1) = q%data(min_idx)%node
    count = 1
    do i = min_idx, q%size - 1
      q%data(i) = q%data(i + 1)
    end do
    q%size = q%size - 1
  end subroutine dq_pull

  subroutine dijkstra(g, source, dist, pred)
    type(Graph), intent(in) :: g
    integer, intent(in) :: source
    real, intent(out) :: dist(:)
    integer, intent(out) :: pred(:)
    type(DQueue) :: q
    real :: Bi
    integer :: S_nodes(MAX_NODES)
    integer :: S_count
    integer :: u, i, v
    real :: w, alt
    integer :: n

    n = g%n
    dist(1:n) = huge(0.0)
    pred(1:n) = -1
    dist(source) = 0.0
    pred(source) = source

    call dq_init(q, n, huge(0.0))
    call dq_insert(q, source, 0.0)

    do while (dq_non_empty(q))
      call dq_pull(q, Bi, S_nodes, S_count)
      do i = 1, S_count
        u = S_nodes(i)
        do v = 1, g%deg(u)
          w = g%edges(u, v)%w
          alt = dist(u) + w
          if (alt < dist(g%edges(u, v)%to)) then
            dist(g%edges(u, v)%to) = alt
            pred(g%edges(u, v)%to) = u
            call dq_insert(q, g%edges(u, v)%to, alt)
          end if
        end do
      end do
    end do
  end subroutine dijkstra

  recursive subroutine bmssp(g, l, B, S, S_count, d_hat)
    type(Graph), intent(in) :: g
    integer, intent(in) :: l
    real, intent(in) :: B
    integer, intent(in) :: S(:)
    integer, intent(in) :: S_count
    real, intent(out) :: d_hat(:)
    integer :: dummy_pred(MAX_NODES)
    if (l <= 0) then
      if (S_count > 0) call dijkstra(g, S(1), d_hat, dummy_pred)
    else
      call bmssp(g, l - 1, B, S, S_count, d_hat)
    end if
  end subroutine bmssp

  subroutine run_sssp(g, source, dist, pred)
    type(Graph), intent(in) :: g
    integer, intent(in) :: source
    real, intent(out) :: dist(:)
    integer, intent(out) :: pred(:)
    call dijkstra(g, source, dist, pred)
  end subroutine run_sssp

  ! -------- Name index for string<->integer mapping --------

  function name_index_of(names, name_count, name) result(idx)
    character(len=MAX_NAME_LEN), intent(in) :: names(:)
    integer, intent(in) :: name_count
    character(len=*), intent(in) :: name
    integer :: idx, i
    idx = -1
    do i = 1, name_count
      if (trim(names(i)) == trim(name)) then
        idx = i
        return
      end if
    end do
  end function name_index_of

  function name_get_or_add(names, name_count, name) result(idx)
    character(len=MAX_NAME_LEN), intent(inout) :: names(:)
    integer, intent(inout) :: name_count
    character(len=*), intent(in) :: name
    integer :: idx
    idx = name_index_of(names, name_count, name)
    if (idx < 0) then
      name_count = name_count + 1
      names(name_count) = trim(name)
      idx = name_count
    end if
  end function name_get_or_add

  subroutine load_graph_from_dot(filename, g, names, name_count, ierr)
    character(len=*), intent(in) :: filename
    type(Graph), intent(out) :: g
    character(len=MAX_NAME_LEN), intent(out) :: names(MAX_NODES)
    integer, intent(out) :: name_count, ierr
    character(len=1024) :: line
    integer :: ios, arrow_pos, bracket_pos, semi_pos, eq_pos, end_pos
    integer :: from_idx, to_idx
    character(len=MAX_NAME_LEN) :: from_name, to_name, weight_str
    real :: weight
    integer, parameter :: MAX_DOT_EDGES = 10000
    integer :: edge_from(MAX_DOT_EDGES), edge_to(MAX_DOT_EDGES)
    real :: edge_wt(MAX_DOT_EDGES)
    integer :: edge_count, i

    ierr = 0
    name_count = 0
    edge_count = 0

    open(unit=10, file=filename, status='old', action='read', iostat=ios)
    if (ios /= 0) then
      ierr = 1
      return
    end if

    do
      read(10, '(A)', iostat=ios) line
      if (ios /= 0) exit

      line = adjustl(line)
      ! Skip empty, comments, digraph header, closing brace
      if (len_trim(line) == 0) cycle
      if (line(1:2) == '//') cycle
      if (index(line, 'digraph') == 1) cycle
      if (trim(line) == '}') cycle

      arrow_pos = index(line, '->')
      if (arrow_pos > 0) then
        ! Parse edge: FROM -> TO [label=WEIGHT];
        from_name = adjustl(line(1:arrow_pos-1))
        from_name = trim(from_name)

        ! Extract TO name (until space, '[', or ';')
        to_name = ''
        i = arrow_pos + 2
        ! skip whitespace after ->
        do while (i <= len_trim(line) .and. line(i:i) == ' ')
          i = i + 1
        end do
        semi_pos = i
        do while (semi_pos <= len_trim(line))
          if (line(semi_pos:semi_pos) == ' ' .or. line(semi_pos:semi_pos) == '[' &
              .or. line(semi_pos:semi_pos) == ';') exit
          semi_pos = semi_pos + 1
        end do
        to_name = trim(line(i:semi_pos-1))

        if (len_trim(from_name) == 0 .or. len_trim(to_name) == 0) cycle

        ! Parse weight from [label=X]
        weight = 1.0
        bracket_pos = index(line, 'label')
        if (bracket_pos > 0) then
          eq_pos = index(line(bracket_pos:), '=')
          if (eq_pos > 0) then
            ! Extract just the numeric portion (stop at ], ;, space, or end)
            eq_pos = bracket_pos + eq_pos  ! absolute position after '='
            end_pos = eq_pos
            do while (end_pos <= len_trim(line))
              if (line(end_pos:end_pos) == ']' .or. line(end_pos:end_pos) == ';' &
                  .or. line(end_pos:end_pos) == ' ') exit
              end_pos = end_pos + 1
            end do
            weight_str = line(eq_pos:end_pos-1)
            read(weight_str, *, iostat=ios) weight
            if (ios /= 0) weight = 1.0
          end if
        end if

        from_idx = name_get_or_add(names, name_count, trim(from_name))
        to_idx = name_get_or_add(names, name_count, trim(to_name))
        edge_count = edge_count + 1
        edge_from(edge_count) = from_idx
        edge_to(edge_count) = to_idx
        edge_wt(edge_count) = weight
      else
        ! Standalone node: NAME;
        semi_pos = index(line, ';')
        if (semi_pos > 1) then
          from_name = trim(adjustl(line(1:semi_pos-1)))
          if (len_trim(from_name) > 0 .and. from_name /= '}') then
            from_idx = name_get_or_add(names, name_count, trim(from_name))
          end if
        end if
      end if
    end do
    close(10)

    if (name_count == 0) then
      ierr = 2
      return
    end if

    call init_graph(g, name_count)
    do i = 1, edge_count
      call add_edge(g, edge_from(i), edge_to(i), edge_wt(i))
    end do
  end subroutine load_graph_from_dot

end module bmssp_module

program main
  use bmssp_module
  implicit none
  character(len=256) :: dot_file, source_name, target_name, arg
  character(len=MAX_NAME_LEN) :: names(MAX_NODES)
  type(Graph) :: g
  real :: dist(MAX_NODES)
  integer :: pred(MAX_NODES)
  integer :: name_count, ierr, source_idx, target_idx
  integer :: i, nargs, iarg
  logical :: verbose, json_out, has_target
  logical :: custom_params
  integer :: param_k, param_t, param_l
  character(len=MAX_NAME_LEN) :: sorted_names(MAX_NODES)
  integer :: sorted_idx(MAX_NODES)
  integer :: path(MAX_NODES), path_len, current

  verbose = .false.
  json_out = .false.
  param_k = 0
  param_t = 0
  param_l = 0
  has_target = .false.
  dot_file = ''
  source_name = ''
  target_name = ''

  nargs = command_argument_count()
  if (nargs == 0) then
    write(0, '(A)') 'Usage: bmssp [OPTIONS] <graph.dot> <source> [target]'
    stop 2
  end if

  iarg = 1
  do while (iarg <= nargs)
    call get_command_argument(iarg, arg)
    select case (trim(arg))
      case ('--verbose')
        verbose = .true.
      case ('--json')
        json_out = .true.
      case ('-V', '--version')
        print '(A)', 'bmssp (Fortran) 0.1.0'
        stop
      case ('-h', '--help')
        write(0, '(A)') 'Usage: bmssp [OPTIONS] <graph.dot> <source> [target]'
        stop
      case ('--k')
        iarg = iarg + 1
        call get_command_argument(iarg, arg)
        read(arg, *) param_k
      case ('--t')
        iarg = iarg + 1
        call get_command_argument(iarg, arg)
        read(arg, *) param_t
      case ('--l')
        iarg = iarg + 1
        call get_command_argument(iarg, arg)
        read(arg, *) param_l
      case default
        if (arg(1:1) == '-') then
          write(0, '(A,A,A)') "bmssp: unknown option '", trim(arg), "'"
          stop 2
        end if
        if (len_trim(dot_file) == 0) then
          dot_file = trim(arg)
        else if (len_trim(source_name) == 0) then
          source_name = trim(arg)
        else if (.not. has_target) then
          target_name = trim(arg)
          has_target = .true.
        else
          write(0, '(A)') 'bmssp: too many arguments'
          stop 2
        end if
    end select
    iarg = iarg + 1
  end do

  if (len_trim(dot_file) == 0 .or. len_trim(source_name) == 0) then
    write(0, '(A)') 'bmssp: invalid arguments'
    write(0, '(A)') 'Usage: bmssp [OPTIONS] <graph.dot> <source> [target]'
    stop 2
  end if

  call load_graph_from_dot(trim(dot_file), g, names, name_count, ierr)
  if (ierr == 1) then
    write(0, '(A,A,A)') 'bmssp: cannot open ', trim(dot_file), ': no such file or directory'
    stop 1
  else if (ierr == 2) then
    write(0, '(A,A,A)') 'bmssp: DOT file ', trim(dot_file), ' did not contain any nodes'
    stop 1
  end if

  source_idx = name_index_of(names, name_count, trim(source_name))
  if (source_idx < 0) then
    write(0, '(A,A,A)') "bmssp: source vertex '", trim(source_name), "' not found in graph"
    stop 1
  end if

  if (has_target) then
    target_idx = name_index_of(names, name_count, trim(target_name))
    if (target_idx < 0) then
      write(0, '(A,A,A)') "bmssp: target vertex '", trim(target_name), "' not found in graph"
      stop 1
    end if
  end if

  custom_params = (param_k > 0) .or. (param_t > 0) .or. (param_l > 0)
  if (custom_params) then
    ! Use BMSSP with custom parameters (no pred tracking)
    call bmssp(g, max(param_l, 1), huge(0.0), (/source_idx/), 1, dist)
    pred = -1
  else
    call run_sssp(g, source_idx, dist, pred)
  end if

  ! Sort names alphabetically for output
  do i = 1, name_count
    sorted_names(i) = names(i)
    sorted_idx(i) = i
  end do
  call sort_names(sorted_names, sorted_idx, name_count)

  if (has_target) then
    if (dist(target_idx) > huge(0.0)/2) then
      if (json_out) then
        print '(A)', '{'
        print '(A,A,A)', '  "source": "', trim(source_name), '",'
        print '(A,A,A)', '  "target": "', trim(target_name), '",'
        print '(A)', '  "distance": null,'
        print '(A)', '  "path": []'
        print '(A)', '}'
      else
        print '(A,A,A,A)', 'no path from ', trim(source_name), ' to ', trim(target_name)
      end if
    else
      ! Reconstruct path by backtracking through pred
      path_len = 0
      if (pred(target_idx) /= -1) then
        current = target_idx
        do while (current /= source_idx .and. path_len < name_count)
          path_len = path_len + 1
          path(path_len) = current
          current = pred(current)
          if (current == -1) exit
        end do
        path_len = path_len + 1
        path(path_len) = source_idx
      else
        ! No pred available (custom params) — just show endpoints
        path_len = 2
        path(2) = source_idx
        path(1) = target_idx
      end if

      if (json_out) then
        print '(A)', '{'
        print '(A,A,A)', '  "source": "', trim(source_name), '",'
        print '(A,A,A)', '  "target": "', trim(target_name), '",'
        print '(A,I0,A)', '  "distance": ', nint(dist(target_idx)), ','
        write(*, '(A)', advance='no') '  "path": ['
        do i = path_len, 1, -1
          write(*, '(A,A,A)', advance='no') '"', trim(names(path(i))), '"'
          if (i > 1) write(*, '(A)', advance='no') ', '
        end do
        print '(A)', ']'
        print '(A)', '}'
      else
        do i = path_len, 1, -1
          write(*, '(A)', advance='no') trim(names(path(i)))
          if (i > 1) write(*, '(A)', advance='no') ' -> '
        end do
        print '(A,I0,A)', ' (distance: ', nint(dist(target_idx)), ')'
      end if
    end if
  else if (json_out) then
    print '(A)', '{'
    print '(A,A,A)', '  "source": "', trim(source_name), '",'
    print '(A)', '  "distances": {'
    do i = 1, name_count
      if (dist(sorted_idx(i)) > huge(0.0)/2) then
        if (i < name_count) then
          print '(A,A,A)', '    "', trim(sorted_names(i)), '": null,'
        else
          print '(A,A,A)', '    "', trim(sorted_names(i)), '": null'
        end if
      else
        if (i < name_count) then
          print '(A,A,A,I0,A)', '    "', trim(sorted_names(i)), '": ', &
                nint(dist(sorted_idx(i))), ','
        else
          print '(A,A,A,I0)', '    "', trim(sorted_names(i)), '": ', &
                nint(dist(sorted_idx(i)))
        end if
      end if
    end do
    print '(A)', '  }'
    print '(A)', '}'
  else
    do i = 1, name_count
      if (dist(sorted_idx(i)) > huge(0.0)/2) then
        print '(A,A,A)', trim(sorted_names(i)), char(9), 'inf'
      else
        print '(A,A,I0)', trim(sorted_names(i)), char(9), nint(dist(sorted_idx(i)))
      end if
    end do
  end if

contains
  subroutine sort_names(snames, sidx, n)
    character(len=MAX_NAME_LEN), intent(inout) :: snames(:)
    integer, intent(inout) :: sidx(:)
    integer, intent(in) :: n
    integer :: i, j, tmp_idx
    character(len=MAX_NAME_LEN) :: tmp_name
    ! Simple insertion sort
    do i = 2, n
      tmp_name = snames(i)
      tmp_idx = sidx(i)
      j = i - 1
      do while (j >= 1 .and. lgt(snames(j), tmp_name))
        snames(j+1) = snames(j)
        sidx(j+1) = sidx(j)
        j = j - 1
      end do
      snames(j+1) = tmp_name
      sidx(j+1) = tmp_idx
    end do
  end subroutine sort_names
end program main
